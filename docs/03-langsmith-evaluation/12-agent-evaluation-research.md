# RAG 평가에서 Agent 평가로 넘어가기 전에 정리한 판단

- 조사일: 2026-07-24
- 상태: Agent 구현 전 평가 방법 조사
- 범위: 공식 문서 검토와 현재 프로젝트 적용 판단

이 문서는 새 평가 도구를 도입하거나 Agent 평가를 실행한 결과가 아니다. 법령 RAG를
LangGraph의 선형 구조로 옮긴 뒤, 앞으로 Node·분기·Tool·loop가 추가되면 무엇을
다르게 평가해야 하는지 미리 생각해본 기록이다. 실제 Dataset 필드와 문항 수,
fixture 계획은
[`Finlife에서 LangGraph Agent까지 확장 명세`](../07-langgraph-agent/01-finlife-agent-expansion-spec.md)에
두고 이 문서에서는 문제를 이해하고 도구를 조사하며 내린 판단만 다룬다.

## 같은 24문항으로 충분하지 않다는 것을 깨달은 이유

LangChain RAG를 `retrieve → generate` LangGraph로 옮길 때는 사용자에게 제공하는
기능이 같았다. 법령을 검색하고 같은 prompt와 모델로 답하는 구조였으므로 같은
24문항으로 검색 결과와 답변이 유지되는지 비교하는 것이 맞았다.

하지만 Agent 확장은 내부 구현만 바꾸는 작업이 아니다. 질문에 따라 법령이나 상품
Tool을 고르고, 조건이 부족하면 추가 질문을 하며, Tool 결과가 없거나 실패하면 다른
종료 방식을 선택하게 된다. 최종 답변이 그럴듯한지만 보면 다음 문제를 구분하기
어렵다.

- 잘못된 Tool을 호출했지만 우연히 맞는 답을 만든 경우
- 올바른 Tool을 골랐지만 기간이나 상품 유형 인자를 잘못 전달한 경우
- 필요한 두 Tool 중 하나를 빠뜨린 경우
- 같은 Tool을 반복하다가 loop 상한에 도달한 경우
- Tool 결과에는 없는 법령·상품·금리를 최종 답변에 추가한 경우

따라서 Node가 늘어서 기존 Dataset이 무효가 되는 것이 아니라, **평가해야 할 계약이
늘어나 기존 reference만으로는 Agent의 행동을 설명할 수 없게 된다**고 이해했다.
[LangSmith 공식 가이드](https://docs.langchain.com/langsmith/evaluation-approaches)도
Agent 평가를 최종 답변, 한 단계의 선택, 전체 실행 경로로 나눈다.

## 기존 Dataset은 버리지 않고 역할을 좁힌다

`rag-v1-dev` 24문항은 법령 검색과 답변의 개발 기준선이다. Agent가 추가되어도 법령
경로가 기존보다 나빠지지 않았는지 확인하는 회귀 평가로 계속 사용할 수 있다.

Agent 전체 평가는 별도 Dataset에서 다음 값을 추가해야 한다.

- 질문별로 필요한 Tool과 호출하면 안 되는 Tool
- Tool 인자가 만족해야 하는 조건
- 순서가 고정된 경로와 순서가 달라도 되는 경로
- 추가 질문, 부분 답변, 오류 안내와 같은 기대 동작
- 최종 답변에 반드시 포함하거나 포함하면 안 되는 주장
- 같은 상품 결과를 재현하기 위한 Finlife fixture 버전

기존 상품 질문은 Tool이 없던 시점에는 “답할 수 없음”이 정답이었지만, 상품 Tool
추가 후에는 “상품 조회”가 정답이 된다. 기존 reference를 고치면 과거 RAG 실험의
의미가 바뀌므로 원본은 보존하고 새 ID와 기준을 가진 Agent Dataset으로 옮긴다.

평가 항목이 늘어난다고 같은 질문을 여러 번 복사할 필요는 없다. Agent 실행 한 건에서
Tool 선택, 인자, 경로, 근거 사용과 최종 답변을 서로 다른 점수로 남길 수 있다.

## 평가를 다섯 층으로 나누어 생각했다

| 층 | 확인할 질문 | 우선 방법 |
| --- | --- | --- |
| 함수·Node | Finlife 응답 결합과 정렬이 맞는가 | mock 기반 단위 테스트 |
| 한 단계 | 다음 Tool과 인자를 맞게 선택했는가 | 코드로 직접 비교 |
| 실행 경로 | 필요한 Tool을 빠뜨리거나 반복하지 않았는가 | Tool 집합·호출 수·허용 순서 비교 |
| 근거 사용 | 답변의 법령·상품·금리가 Tool 결과에 있는가 | ID와 값을 코드로 비교 |
| 최종 답변 | 질문을 해결하고 한계와 부분 실패를 설명했는가 | rubric 기반 Judge와 사람 검토 |

모든 경로에 정확히 같은 Node 순서를 강제하지 않는다. 혼합 질문은 법령 다음 상품을
조회해도 되고 상품 다음 법령을 조회해도 된다. 반면 검증 없이 쓰기 작업을 실행하는
것처럼 순서가 안전과 직접 연결되는 경우에는 정확한 경로 검사가 필요하다. 현재
Agent의 Tool은 조회 전용이므로 필요한 Tool 집합, 잘못된 추가 호출과 최종 근거를
우선해서 본다.

코드로 확정할 수 있는 Tool 이름, 인자, 호출 수와 상품 값은 LLM Judge에게 맡기지
않는다. Judge는 설명의 충분함처럼 문장 의미를 봐야 하는 항목에만 사용한다. 그래야
비용과 실행별 판정 차이를 줄이고, 실패 원인도 쉽게 찾을 수 있다.

## 오픈소스와 플랫폼을 찾아보며 구분한 것

LangSmith를 사용하면서 trace에서 검색과 생성 단계를 보고, 같은 Dataset의
Experiment를 화면에서 비교하는 편리함을 경험했다. 반면 Agent가 되면 Tool 경로와
인자, 반복 호출 같은 프로젝트 기준을 직접 evaluator 코드로 더 작성해야 한다.
그래서 코드를 적게 쓰면서도 평가 결과를 비교하고 시각화할 수 있는 다른 도구가
있는지 찾아봤다.

조사해보니 같은 “Agent 평가 도구”라는 이름 아래 역할이 다른 세 종류가 섞여 있었다.

| 종류 | 조사한 후보 | 확인한 특징 |
| --- | --- | --- |
| 경로·지표 라이브러리 | [AgentEvals](https://github.com/langchain-ai/agentevals), [DeepEval](https://deepeval.com/docs/metrics-introduction), [Ragas](https://docs.ragas.io/en/v0.4.2/concepts/metrics/available_metrics/agents/) | 기존 평가 실행에 Tool 경로·정확성 지표를 추가 |
| 로컬 평가·추적 도구 | [Promptfoo](https://www.promptfoo.dev/docs/tracing/), [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evaluators/span-based/) | trace를 받아 Tool·순서·오류·loop 조건을 검사하고 로컬 결과 확인 |
| 관측·평가 플랫폼 | [Opik](https://github.com/comet-ml/opik), [Langfuse](https://github.com/langfuse/langfuse) | trace, Dataset, Experiment, Judge와 대시보드를 함께 제공 |

[Inspect AI](https://inspect.aisi.org.uk/)와
[τ-bench](https://github.com/sierra-research/tau2-bench)처럼 도구를 사용하는 Agent를
격리된 환경이나 사용자 시뮬레이션에서 평가하는 공개 벤치마크도 확인했다. 이들은
현재 법령·상품 POC에 바로 붙일 작은 evaluator라기보다, 나중에 대화가 길어지고
Agent가 외부 상태를 바꾸게 될 때 참고할 평가 방법에 가깝다.

공식 문서를 비교하면서 다음을 배웠다.

- 평가 라이브러리와 대시보드 플랫폼은 대체 관계가 아닐 수 있다.
- 준비된 지표가 많아도 현재 trace 형식으로 변환하는 코드가 필요할 수 있다.
- 로컬 실행과 오픈소스 SDK가 가능해도 협업 화면이나 운영 기능은 별도 서비스일 수
  있다.
- 정확한 경로 하나를 강제하는 기능보다 여러 정상 경로와 금지 동작을 표현할 수
  있는지가 중요하다.
- 새 플랫폼을 추가하면 LangSmith와 trace·Dataset 관리가 중복될 수 있다.

## 현재 내린 도구 선택

지금은 아직 Finlife client와 상품 Node도 구현하기 전이므로 평가 도구를 설치하지
않는다. Tool 이름과 schema, Agent message, 실제 trace가 정해지지 않은 상태에서
라이브러리를 먼저 선택하면 그 도구의 입력 형식에 맞춰 Agent 설계를 끌고 갈 수 있기
때문이다.

첫 tool-calling Agent가 동작하면 다음 순서로 확인한다.

1. LangSmith를 trace와 Experiment 비교 화면으로 계속 사용
2. Tool 이름·인자·반복·근거 일치는 작은 코드 evaluator로 먼저 작성
3. 대표 사례 몇 개로 AgentEvals의 LangGraph message·경로 호환성 확인
4. 직접 작성할 경로 비교 코드를 실제로 줄여준다면 AgentEvals 채택
5. 최종 답변의 의미 평가는 기존 Judge를 확장하되 경로 점수와 분리

AgentEvals는 정확·순서 무관·부분 경로 비교와 Tool 인자 비교를 제공해 현재 구조에
가장 가까운 첫 후보였다. DeepEval과 Ragas는 여러 준비된 Agent 지표가 필요할 때,
Promptfoo와 Pydantic Evals는 OpenTelemetry 기반 loop·오류 검사나 CI가 필요할 때
다시 비교한다. 자체 호스팅이나 LangSmith 의존 제거가 실제 요구가 될 때만
Opik·Langfuse 같은 플랫폼 전환을 검토한다.

## 첫 Agent 평가 전에 다시 확인할 것

- Tool 이름과 입력 schema가 작은 구현을 거쳐 안정됐는가
- Agent 실행 결과가 `messages`, `tool_calls`, 인자와 종료 이유를 보존하는가
- 법령·상품·혼합·추가 질문·오류 경로가 Dataset에 모두 포함됐는가
- 하나의 정답 경로가 아니라 허용 Tool 집합과 금지 동작을 표현했는가
- 상품 품질 평가는 live API가 아니라 고정 fixture로 재현되는가
- 결정적 코드 점수와 LLM Judge 점수가 별도 feedback으로 보이는가
- 개발에 사용하지 않은 held-out 질문을 첫 기준선 뒤에 마련했는가
- 새 라이브러리가 기존 코드와 비교 화면을 실제로 줄여주는가

## 이 경험에서 설명할 수 있는 것

단순한 프레임워크 마이그레이션에서는 기능 계약이 같아 기존 Dataset을 고정하고
전후를 비교했다. 이후 Agent로 확장하면서 최종 답변만으로는 Tool 선택과 중간 실패를
알 수 없다는 점을 발견했고, 기존 24문항을 법령 회귀 평가로 보존하면서 Agent 행동
기준을 가진 새 Dataset을 분리하기로 했다.

또한 익숙한 LangSmith를 바로 버리거나 유명한 평가 도구를 먼저 도입하지 않았다.
공식 문서에서 라이브러리·로컬 도구·플랫폼·벤치마크의 역할을 구분하고, 현재
프로젝트에서는 LangSmith와 결정적 evaluator를 유지한 뒤 실제 tool-calling trace가
생겼을 때 AgentEvals를 작은 사례로 검증하는 순서를 선택했다. 이 과정은 평가 점수
자체뿐 아니라 평가가 어떤 실패를 설명해야 하는지 먼저 설계한 경험으로 정리할 수
있다.

관련 기록:

- [`RAG 평가 질문`](02-rag-questions.md)
- [`LangChain RAG를 LangGraph로 옮긴 뒤 평가해본 결과`](11-langgraph-migration-results.md)
- [`Finlife에서 LangGraph Agent까지 확장 명세`](../07-langgraph-agent/01-finlife-agent-expansion-spec.md)
