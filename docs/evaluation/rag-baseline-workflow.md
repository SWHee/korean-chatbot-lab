# RAG 기준선 평가 순서

이 문서는 현재 LangChain RAG를 평가한 뒤 LangGraph로 옮기기로 한 이유와 작업
순서를 정리한다. 목표는 높은 점수를 만드는 것이 아니라, 구조를 바꾸기 전과 후를
같은 기준으로 비교하는 것이다.

## 무엇을 먼저 하나

LangGraph 마이그레이션보다 Dataset 기반 기준선 평가를 먼저 진행한다.

```text
평가 기준 확정
  → 현재 LangChain RAG 기준선 실행
  → 실패 사례 확인
  → StateGraph로 구조만 마이그레이션
  → 같은 Dataset으로 다시 실행
  → 두 결과 비교
```

이 순서가 필요한 이유는 비교 기준을 남기기 위해서다. LangGraph로 먼저 옮기고 나면
답변이 달라졌을 때 원래 RAG의 한계인지, 마이그레이션 과정에서 생긴 변화인지
구분하기 어렵다. 현재 결과를 먼저 남기면 StateGraph 전환 뒤 검색 품질과 답변
품질이 유지됐는지 같은 질문과 평가 항목으로 확인할 수 있다.

LangSmith의 offline evaluation도 Dataset을 만들고, evaluator를 정한 뒤,
애플리케이션을 실행해 experiment를 비교하는 순서다. 따라서 지금 결정은 프로젝트
학습 순서뿐 아니라 도구가 제공하는 평가 흐름과도 맞는다.

## 세부 워크플로우

1. **Dataset v1 계약 확정**: 질문 입력, 기대 근거, 질문 유형과 평가 가능 범위를
   정한다. (완료)
2. **로컬 Dataset 생성**: 24개 질문을 reference answer와 문항별 rubric이 있는
   JSONL로 변환한다. (완료)
3. **LangSmith Dataset 등록**: 검증된 JSONL 질문과 정답 조건을 LangSmith에
   올린다.
4. **평가 대상 연결**: 질문 하나로 현재 RAG를 실행해 답변·검색 출처·조문 본문을
   돌려주는 `run_rag_evaluation()`을 구현했다. LangSmith experiment 연결은 다음
   단계에서 진행한다.
5. **작은 evaluator 구현**: `score_retrieval_at_5()`로 ID 기반 Context
   Precision@5·Recall@5를 계산하고, `langsmith_retrieval_evaluator`로 LangSmith
   실행 결과와 연결했다.
6. **기준선 experiment 실행**: 로컬 모델의 동시 실행을 피하기 위해 처음에는
   한 요청씩 실행한다.
7. **결과 확인과 기록**: 전체 평균만 보지 않고 실패한 질문과 원인을 검색·생성으로
   나누어 확인한다.
8. **StateGraph 마이그레이션**: 검색과 답변 생성 기능은 유지하고 실행 구조만
   graph node로 옮긴다.
9. **같은 Dataset 재평가**: 기준선 experiment와 나란히 비교해 회귀 여부를
   확인한다.

금융상품 한눈에 API와 질문 분기는 이 비교가 끝난 뒤 추가한다. 구조 변경과 기능
추가를 동시에 하면 어떤 변화가 결과에 영향을 줬는지 설명하기 어려워지기 때문이다.

## Dataset v1 계약

첫 단계에서 다음 계약을 확정했고, `data/evaluation/rag-v1-dev.jsonl`에 반영했다.

| 구분 | 저장할 값 | 용도 |
| --- | --- | --- |
| 입력 | `question` | 현재 RAG에 전달할 질문 |
| 식별 정보 | 질문 ID와 유형(A~E) | 유형별 결과 확인 |
| 기대 근거 | 법령명과 조문번호 목록 | retrieval 결과 점검 |
| 기대 동작 | 근거 답변, 전제 교정, 범위 밖 안내 등 | 답변의 역할 확인 |
| 평가 가능 여부 | retrieval 평가 대상 여부 | 현행 조문에 없는 질문의 오채점 방지 |

질문은 [`rag-questions.md`](rag-questions.md)의 24개를 사용한다. 그중 정답 조문이
원문에서 확인된 15개만 정답 조문 포함 여부를 계산한다. A5, B2, B3처럼 현행 조문
문면만으로 확인하기 어려운 질문과 D·E 유형에는 같은 retrieval 점수를 억지로
적용하지 않는다.

자연어 답변은 표현이 달라질 수 있으므로 exact match를 사용하지 않는다. 대신
`reference_answer`, `required_claims`, `forbidden_claims`를 함께 두었다. 검색은
정답 조문 ID로 결정적으로 평가하고, 답변 내용은 실제 검색 문맥과 rubric을 받은
LLM-as-a-Judge로 평가한다.

현재 Dataset v1은 세션⑤의 초기 정답 조문에서 A2·A6·C2의 필수 조문을 확장했다. 법령
근거를 더 온전하게 반영한 변경이지만 평가 기준 자체가 달라졌으므로, 세션⑤ 수치와
Dataset v1 수치를 직접 비교하지 않는다. LangSmith experiment에는 최소한
`dataset=rag-v1-dev`와 `corpus_snapshot=2026-07-06`을 기록한다.

## 검색 지표의 계산 기준

첫 기준선은 Judge 없이 조문 ID로 계산할 수 있는 두 지표부터 구현한다.

- ID 기반 Context Recall@5 = top-5에서 찾은 필수 정답 조문 수 / 전체 필수 정답 조문 수
- ID 기반 Context Precision@5 = top-5 중 필수 또는 보조 정답 조문인 조문 수 /
  실제 반환된 조문 수

`required_claims`는 Context Recall에 포함하지 않는다. 검색 지표는 어떤 조문을
찾았는지 평가하고, 필수·금지 주장은 생성 답변 평가에서 별도로 확인한다.

## LLM Judge는 아직 미선정

OpenAI·Claude·Gemini 계열을 후보로 두고, 같은 답변 일부를 채점한 결과가 사용자
판단과 얼마나 일치하는지 비교한 뒤 선택한다. 특정 모델이나 API key가 준비됐다고
가정하지 않는다. 선택된 Judge는 법률 정답을 새로 만드는 역할이 아니라 질문,
reference, 실제 검색 문맥, 생성 답변을 함께 받아 다음을 판정한다.

- 답변의 주장이 검색 문맥에서 확인되는가(Faithfulness)
- 질문을 직접 다루며 불필요하게 벗어나지 않는가(Answer Relevancy)
- 어떤 `required_claims`를 충족했는가
- 어떤 `forbidden_claims`를 위반했는가

Judge 출력에는 점수만 두지 않고 충족한 필수 주장과 위반한 금지 주장의 목록을
분리한다. 특히 Faithfulness를 적용하지 않는 A5·B2·B3·D·E의 9문항은 금지 주장
위반을 별도로 확인해야 근거 없는 답변을 놓치지 않는다.

첫 experiment에서는 judge 점수를 그대로 믿지 않고 24개 결과를 모두 직접 확인한다.
사람 판단과 Judge 점수가 다르면 Dataset rubric 또는 judge prompt 중 어느 쪽이
불명확한지 먼저 살펴본다.

## dev와 held-out 구분

현재 24개 중 15개는 임베딩 모델 선택과 검색 검증에 이미 사용했다. 따라서
`rag-v1-dev.jsonl`은 현재 RAG와 LangGraph 전환 결과를 비교하는 개발·회귀
Dataset이다. 독립적인 최종 성능으로 과장하지 않는다.

기준선 평가 흐름이 동작한 뒤에는 새 질문 10~12개를 작성해 held-out test로
분리한다. held-out test는 모델이나 검색 설정을 고를 때 사용하지 않고 마지막에만
확인하는 새 시험 문제다. 가능하면 기존 정답 조문에 없던 조문도 포함하고, 평가 결과가
마음에 들지 않는다는 이유로 질문이나 정답을 바꾸지 않는다.

## 다음 작업을 쉬운 말로 정리하면

현재는 시험 문제와 채점 기준을 파일로 만든 상태다. 다음에는 질문 하나를 실제 RAG에
넣고 아래 결과를 한 묶음으로 받는 작은 함수를 만든다.

```text
질문
  → 검색된 법령 본문
  → 출처 목록
  → 생성된 답변
```

이 함수가 있어야 "정답 조문을 찾았는가", "찾은 조문만 사용해 답했는가",
"질문에 맞게 답했는가"를 각각 계산할 수 있다. 그 다음 이 24문항을 LangSmith에
올려 같은 과정을 반복 실행한다.

## 이 단계의 완료 기준

- Dataset의 24개 질문이 ID와 유형을 유지한다.
- retrieval 평가 대상 15개와 제외 질문이 구분된다.
- 현재 LangChain RAG experiment가 한 번 실행된다.
- 같은 Dataset을 StateGraph 평가에서도 수정 없이 다시 사용할 수 있다.

참고:

- [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation)
- [LangSmith experiment 비교](https://docs.langchain.com/langsmith/compare-experiment-results)
- [Ragas Context Precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)
- [Ragas Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)
- [Ragas Faithfulness](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/)
- [Ragas Answer Relevancy](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/answer_relevance/)
