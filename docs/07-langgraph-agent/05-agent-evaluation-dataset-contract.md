# Agent 개발 Dataset 계약

- 작성일: 2026-08-03
- 상태: Dataset·fixture 계약 완료, 첫 Experiment 실행 전
- 대상: Tool Calling과 멀티턴 Clarify를 포함한 Agent Graph

## 왜 별도 Dataset인가

기존 `rag-v1-dev` 24문항은 법령 검색과 답변 품질의 회귀 확인용이다. Agent에서는
최종 답변뿐 아니라 법령·상품 Tool 선택, 인자, 반복 호출, 두 턴 조건 병합도 확인해야
한다. 그래서 기존 Dataset을 고치지 않고 `agent-v1-dev`를 새로 만들었다.

이 작업은 Agent를 이미 32번 평가해 점수를 낸 결과가 아니다. 이후 같은 조건으로
실행하고 비교할 수 있도록 **기대 행동을 고정한 준비 작업**이다.

## Dataset 구성

기계 판독용 파일은
[`agent-v1-dev.jsonl`](../../data/evaluation/agent-v1-dev.jsonl)이다.

| 유형 | 사례 수 | 확인할 동작 |
| --- | ---: | --- |
| 법령 | 8 | 법령 Tool 선택과 근거 안내 |
| 상품 | 8 | 정기예금 Tool 인자와 비교 기준 |
| 혼합 | 8 | 두 Tool 호출 집합과 결과 결합 |
| 경계 | 8 | Tool 불필요, 범위 밖, 후보 없음, 미지원 상품 |

이 중 상품 4개와 혼합 4개는 두 턴 trajectory다. 첫 턴은 `clarify`와 부족한 조건을,
둘째 턴은 `ready`와 최종 Tool 호출을 기록한다.

한 사례의 핵심 필드는 다음과 같다.

```text
id, category, turns
turn.message
turn.expected_route
turn.expected_tools[name, arguments, expected_status]
turn.expected_missing_fields
```

Tool 호출 순서는 고정하지 않는다. 현재 Tool은 조회 전용이므로, 혼합 질문에서는
필요한 Tool 집합·인자·불필요한 반복이 없는지를 먼저 평가한다.

## 상품 fixture를 고정한 이유

Finlife 공시 데이터는 시간에 따라 달라진다. 따라서 상품 후보·금리·순위를 live API로
평가하면 Agent를 바꾸지 않아도 점수가 달라질 수 있다.

상품 Tool이 필요한 사례는
[`finlife-deposit-v1.json`](../../data/evaluation/finlife-deposit-v1.json)을
가리킨다. 실제 Finlife 호출은 연결 smoke에만 사용하고, 평가에서는 이 fixture를
주입한다.

## LangSmith 등록과 실행 경계

기존 RAG에는 다음 코드가 있다.

| 파일 | 역할 |
| --- | --- |
| `scripts/register_evaluation_dataset.py` | RAG JSONL을 LangSmith Dataset으로 등록 |
| `scripts/run_rag_evaluation.py` | RAG target과 retrieval·Faithfulness evaluator 실행 |

이 스크립트는 RAG 24문항의 `question → answer` 계약에 맞춘 것이다. Agent Dataset에는
중첩된 두 턴과 Tool 기대값이 있으므로 그대로 복사하지 않는다.

첫 등록은 LangSmith 웹 UI에서 한다.

1. **Datasets & Experiments → New Dataset → Import existing dataset**을 연다.
2. `agent-v1-dev.jsonl`을 먼저 소수 사례로 import해 입력·참조 필드 표시를 확인한다.
3. 검토 뒤 전체 32사례를 `korean-chatbot-agent-v1-dev` 이름으로 등록한다.
4. `dataset_version`, `category`, `finlife_fixture_version`을 metadata로 유지한다.

LangSmith는 UI에서 CSV·JSONL import와 Dataset schema 설정을 지원한다. 다만 이 UI
기능은 Dataset을 저장·비교하기 위한 것이며, Tool 인자와 loop를 자동으로 맞다고
판단하지는 않는다. 다음 구현에서 Graph 실행 결과의 Tool 호출을 Dataset 계약과
비교하는 결정적 evaluator를 추가한다.

공식 UI import와 Dataset schema 안내는
[LangSmith Dataset 관리 문서](https://docs.langchain.com/langsmith/manage-datasets-in-application)를
따른다.

## 현재 확인과 다음 단계

코드 계약은 32사례의 유형 분포, 8개 멀티턴 trajectory, 상품 Tool 사례의 fixture
버전 연결을 검사한다. 아직 실제 Claude API·live Finlife API를 호출하거나 LangSmith
Experiment를 만들지 않았다.

다음 작은 작업은 fixture를 실제 Tool에 주입하고, Tool 이름·인자·호출 집합·반복을
코드로 채점하는 Agent evaluation target을 만드는 것이다. Agent API는 그 다음
단계에서 Swagger로 연결한다.
