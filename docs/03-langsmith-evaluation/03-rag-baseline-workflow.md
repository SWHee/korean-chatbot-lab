# RAG 기준선 평가 순서

- 작성일: 2026-07-14

이 문서는 현재 LangChain RAG를 먼저 평가하고 LangGraph로 옮기는 순서를 정리한다.
목표는 점수를 높게 만드는 것이 아니라, 실행 구조가 바뀌기 전과 후를 같은 기준으로
비교하는 것이다.

## 전체 순서

```text
평가 질문과 채점 기준 확정
  → LangChain v1 기준선 실행
  → 실패 문항 확인
  → 같은 기능을 StateGraph로 이동
  → 같은 Dataset으로 다시 평가
  → 두 결과 비교
```

LangGraph를 먼저 구현하면 답변 변화가 기존 RAG의 한계인지, 옮기는 과정에서 생긴
문제인지 구분하기 어렵다. 현재 결과를 먼저 남겨 두면 검색과 답변 품질이 유지됐는지
문항별로 확인할 수 있다.

## 현재까지 완료한 단계

| 단계 | 산출물 | 상태 |
| --- | --- | --- |
| 평가 질문 확정 | `02-rag-questions.md` | 완료 |
| 로컬 Dataset 작성 | `data/evaluation/rag-v1-dev.jsonl` 24문항 | 완료 |
| LangSmith Dataset 등록 | `korean-chatbot-rag-v1-dev` | 완료 |
| 평가용 LangGraph target 연결 | `create_graph_evaluation_target()` | 완료 |
| 검색 evaluator 연결 | `precision_top_5`, `recall_top_5` | 완료 |
| 답변 evaluator 연결 | Gemini 3.5 Flash Faithfulness | 완료 |
| LangChain v1 기준선 | 단일 Experiment 24문항 | 완료 |
| StateGraph 전환 | 같은 검색·생성 기능 이동 | 다음 단계 |

기준선 결과와 문항별 해석은
[`LangChain v1 기준선 결과`](06-langchain-baseline-results.md)에 기록한다.

## Dataset과 평가 범위

Dataset은 다섯 유형의 24문항으로 구성한다.

- A: 법령 근거형
- B: 개정시점·시행일형
- C: 잘못된 전제형
- D: 현재 범위 밖의 상품 질문
- E: 일반 금융 개념 대조군

정답 조문을 원문에서 확인할 수 있는 15문항만 검색 Precision과 Recall을 계산한다.
A5·B2·B3와 D·E 유형 9문항은 현재 corpus로 정답 조문을 정할 수 없어 검색 점수가
`N/A`다. 이 질문들은 범위 밖 내용을 지어내지 않는지 사람이 확인하고, 이후 상품
API와 질문 분기가 추가됐을 때 동작 변화를 비교하기 위해 Dataset에 남긴다.

자세한 필드와 제외 기준은
[`data/evaluation/README.md`](../../data/evaluation/README.md)에 정리한다.

## 사용한 지표

- `precision_top_5` = 상위 5개 중 필수·보조 정답 조문의 비율
- `recall_top_5` = 전체 필수 정답 조문 중 상위 5개에서 찾은 비율
- `faithfulness` = 생성 답변의 사실 주장이 실제 검색 문맥에 근거하는 정도

검색 지표는 조문 ID로 계산하고, Faithfulness만 LLM Judge가 평가한다. 검색 결과를
코드로 비교할 수 있는데도 LLM에게 다시 추측시키지 않기 위해 역할을 나눴다.

Faithfulness는 `0`, `0.5`, `1` 세 단계다. 질문에 충분히 답했는지와 정답을 완전히
말했는지는 포함하지 않는다. 예를 들어 필요한 조문을 찾지 못한 뒤 "확인할 수 없다"고
답하면 Recall은 낮고 Faithfulness는 높을 수 있다.

## 기준선 실행 방식

로컬 Ollama 모델이 한 번에 한 요청만 처리하도록 `max_concurrency=1`을 사용했다.
API 한도가 초기화된 뒤 24문항을 한 번에 실행했다.

```bash
uv run python scripts/run_rag_evaluation.py --all
```

이전에 완료한 10문항·14문항 분할 실행은 한도 문제를 피하면서 평가 흐름을 확인한
보조 기록이다. 최종 기준선은 RAG 실행 24건과 평가 대상 15문항의 세 지표가 모두
있는 단일 Experiment다.

처음 실행에서 겪은 `No Feedback`과 API 한도 문제는
[`첫 기준선 평가 문제 해결`](08-langchain-baseline-troubleshooting.md)에 정리한다.

## LangGraph 비교에서 고정할 조건

첫 StateGraph 전환에서는 다음 값을 바꾸지 않는다.

- Dataset `rag-v1-dev`
- 법령 corpus snapshot `2026-07-06`
- KURE-v1 임베딩과 Chroma 인덱스
- 조문 단위 top 5 검색
- 현재 RAG prompt와 Ollama Qwen3 모델
- Gemini 3.5 Flash Judge와 세 단계 Faithfulness 기준

처음에는 실행 구조만 바꿔야 결과 차이를 LangGraph 전환의 영향으로 설명할 수 있다.
금융상품 API, 질문 분기, prompt 개선은 구조가 같은 기능을 내는지 확인한 뒤 별도
단계로 추가한다.

## 기준선 완료 기준

- Dataset 24문항의 ID와 유형이 유지됨
- 단일 Experiment에 중복·누락 없이 24문항이 있고 RAG 실행 오류가 없음
- 검색 평가 대상 15문항의 Precision·Recall이 모두 존재함
- 같은 15문항의 Faithfulness가 모두 존재함
- 문항별 실패 원인과 현재 한계를 사람이 확인함

현재 LangChain v1 기준선은 이 조건을 충족한다. 다음 작업은
[`LangGraph 전환 계획`](../04-langgraph-migration/01-langgraph-migration-plan.md)의 첫 단계부터 작은
단위로 진행한다.

참고:

- [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation)
- [LangSmith Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
