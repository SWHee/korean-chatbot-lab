# 생성 모델 교체 시 다시 평가할 범위

- 작성일: 2026-08-01
- 상태: 평가 범위 결정, Claude 24문항 비교 전
- 비교 대상: Ollama Qwen3 4B → Anthropic Claude Haiku

## 결론

기존 24문항 Dataset과 Ollama baseline을 새로 만들 필요는 없다. 질문, 정답 조문,
법령 corpus와 검색 설정을 그대로 두어야 모델 하나만 바꾼 비교가 된다.

다만 Claude 답변의 품질과 속도는 과거 결과로 알 수 없으므로, **같은 24문항을 Claude로
한 번 더 실행한 새 experiment**는 필요하다. 이는 baseline을 다시 만드는 작업이 아니라
기존 baseline 옆에 생성 모델 비교 결과를 추가하는 작업이다.

## 어느 단계가 지표를 바꾸는가

현재 Graph는 다음과 같은 고정된 선형 구조다.

```text
질문 → retrieve → 검색 조문 → generate → 최종 답변
         │                         │
         └─ Precision·Recall       └─ Faithfulness·답변 품질·속도
```

| 평가 대상 | 직접 영향을 주는 요소 | Claude 교체 후 판단 |
| --- | --- | --- |
| Precision@5 | corpus, 청킹, 임베딩, 검색 방식, `top_k` | 원칙적으로 동일 |
| Recall@5 | corpus, 정답 조문, 임베딩, 검색 방식, `top_k` | 원칙적으로 동일 |
| Faithfulness | 검색 문맥과 생성된 답변 | 다시 평가 필요 |
| 답변의 정확성·충분함 | 생성 모델, system prompt, 검색 문맥 | 다시 평가 필요 |
| 말투·가독성 | 생성 모델과 prompt | 자동 지표 외 수동 확인 필요 |
| 응답 길이·Latency | 생성 모델, 출력 토큰 수, API 통신 | 다시 측정 필요 |
| 비용 | 공급자와 입력·출력 토큰 | 새로 기록 필요 |

현재 Precision은 상위 5개 검색 조문 중 정답 또는 보조 조문이 차지하는 비율이다.
Recall은 반드시 찾아야 하는 정답 조문 중 실제로 찾은 비율이다. 두 값은 Claude가
답변을 생성하기 전에 이미 결정된다. 같은 index와 설정에서도 실행 환경이나 동점
결과를 확인할 수 있으므로 새 experiment에서 다시 계산할 수는 있지만, 생성 모델의
성능 개선으로 해석해서는 안 된다.

반대로 Faithfulness는 **생성된 답변의 사실 주장이 검색 문맥에 근거하는지** 평가한다.
같은 조문을 받아도 모델마다 선택하는 내용과 표현이 달라지므로 반드시 다시 채점해야
한다. 현재 Faithfulness evaluator는 답변의 친절함, 길이, 문체와 완전성을 평가하지
않으므로, 점수가 높아도 상담 답변의 품질이 좋다는 뜻은 아니다.

## Claude와 Gemini의 역할 구분

| 역할 | 현재 모델 | 하는 일 |
| --- | --- | --- |
| 평가 대상 | Claude Haiku | 검색 조문을 바탕으로 사용자 답변 생성 |
| 평가자 | Gemini 3.5 Flash | 생성된 답변의 Faithfulness 채점 |

생성 모델을 Claude로 바꿨다고 평가자까지 바꾸면 두 변수가 동시에 달라진다. 따라서
Ollama 결과와 공정하게 비교하려면 Gemini 모델, 평가 prompt와 점수 기준을 유지하는
편이 적절하다. Claude가 자신의 답변을 직접 채점하지 않는다는 장점도 있다.

다만 LLM 평가자도 항상 정답은 아니다. Gemini 오류가 난 문항은 점수 없음으로 구분해
재실행하고, 대표 답변은 사람이 함께 확인한다. 모델 교체 목적이 한국어 상담 품질
개선인 만큼 최소한 다음 항목은 수동 비교가 필요하다.

- 질문에 직접 답했는지
- 필요한 설명이 빠지지 않았는지
- 금융 상담에 어울리는 친절하고 자연스러운 말투인지
- 근거 부족을 과도하게 단정하거나 장황하게 반복하지 않는지

## 이번 비교 실행 원칙

1. 기존 Ollama experiment와 24문항 Dataset 보존
2. corpus, KURE-v1, Chroma, `top_k`, RAG prompt와 평가자 고정
3. 생성 backend만 Claude로 변경
4. 새 `generation-comparison` experiment로 실행
5. Faithfulness, 답변 내용, 응답 길이, Latency와 비용 비교
6. 대표 성공·근거 부족 답변을 사람이 나란히 확인

먼저 문항 1개로 API와 evaluator 동작을 확인한 뒤 24문항을 실행한다. 기존 Retrieval
점수와 차이가 생기면 Claude 효과로 해석하지 않고 index, corpus 또는 검색 설정이 함께
바뀌었는지부터 확인한다.

## Agent 확장 이후 달라지는 점

이 구분은 현재 `retrieve → generate` 구조에 대한 판단이다. 이후 모델이 검색 질문을
다시 작성하거나, 검색 Tool 호출 여부·횟수·인자를 선택하면 생성 모델의 판단이 검색
경로에도 영향을 준다. 그 단계에서는 다음 항목도 별도로 평가해야 한다.

- 올바른 Tool과 route 선택
- 검색 질문과 Tool 인자의 정확성
- 예상한 Node·Tool 실행 경로 준수
- 불필요한 반복 호출과 Loop 종료
- 각 단계 결과와 최종 답변 품질

따라서 기존 24문항은 법령 RAG 경로의 회귀 평가와 생성 모델 비교에는 재사용하지만,
Agent 전체 평가는 경로와 Tool 선택 정답이 포함된 새 Dataset을 추가한다.

## 면접에서 설명할 핵심

> 현재 Graph에서는 검색이 생성보다 먼저 독립적으로 끝나므로 생성 모델을 바꿔도
> Precision과 Recall은 원칙적으로 바뀌지 않습니다. 반면 Faithfulness, 답변 품질,
> 길이와 Latency는 생성 결과에 의존하므로 같은 Dataset으로 다시 비교해야 합니다.

> Gemini는 답변 생성기가 아니라 고정된 평가자입니다. 평가자까지 함께 바꾸면 결과
> 차이가 Claude 때문인지 채점 기준 때문인지 구분할 수 없어 기존 설정을 유지했습니다.

관련 구현과 전환 배경은
[`Agent 확장 전 생성 모델 backend 전환 계획`](02-generation-model-backend-transition.md),
Agent 평가 Dataset의 확장 방향은
[`RAG 평가에서 Agent 평가로 넘어가기 전에 정리한 판단`](../03-langsmith-evaluation/12-agent-evaluation-research.md)을 참고한다.
