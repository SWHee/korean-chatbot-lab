# Finlife에서 LangGraph Agent까지의 실행 명세

- 최초 작성: 2026-07-24
- 재정리: 2026-07-28
- 상태: Finlife client 구현 전
- 현재 기준선: Git `f6e5334` 이후 작업 트리의 법령 RAG v2

## 문서 역할

이 문서는 Finlife client부터 Agent v1까지의 **구현 순서와 단계별 완료 조건**만
관리한다. 앞으로 작업을 시작할 때는 해당 단계 한 절만 우선 참고한다.

중복되는 배경은 다음 문서에 둔다.

- Finlife 응답 필드와 실제 호출 결과:
  [`외부 데이터와 API`](../06-other/01-external-data-sources.md)
- Agent 평가가 기존 24문항과 달라지는 이유:
  [`RAG 평가에서 Agent 평가로 넘어가기 전에 정리한 판단`](../03-langsmith-evaluation/12-agent-evaluation-research.md)
- 현재 법령 Graph와 LCEL의 역할:
  [`LangGraph로 마이그레이션한다는 의미`](../04-langgraph-migration/03-what-langgraph-migration-means.md)

완료된 과거 계획과 이 문서의 미래 순서가 다르면 이 문서를 따른다.

## 현재 기준선과 지켜야 할 경계

현재 법령 RAG는 다음 경로다.

```text
START → retrieve → generate → END
```

- `src/chatbot/graph.py`의 `create_rag_graph()`와 기존 RAG endpoint 유지
- 기존 법령 XML, KURE-v1, Chroma, 검색 상위 5개 설정 유지
- `rag-v1-dev` 24문항은 법령 경로의 회귀 평가로만 사용
- Finlife 인증키는 환경 변수에서만 읽고 State, Tool 인자, 로그, trace에서 제외
- 상품 정보는 개인화 추천이 아니라 현재 공시된 비교 후보로 안내
- 새 기능은 아래 순서에서 한 단계씩 구현하고 검증한 뒤 다음 단계로 이동

## 단계 이름

| 이름 | 의미 | 완료 기준 |
| --- | --- | --- |
| Finlife Client POC | 외부 API 호출과 응답 계약 검증 | 고정 입력 한 건의 정상·본문 오류 처리 |
| Product Node POC | 검증된 client를 Graph Node로 연결 | State에 상품 후보 추가 |
| Routed Workflow POC | 코드가 정한 조건부 경로 검증 | 법령·상품 분기와 혼합 합류 |
| Routed Workflow v1 | 사용자 질문을 받아 끝까지 답변 | 비스트리밍 API와 오류 계약 |
| Tool-calling Agent POC | 모델이 Tool과 반복 여부를 선택 | 단일·혼합 Tool 호출과 종료 |
| Agent v1 | 평가 가능한 첫 Agent 기준선 | Dataset, trace, API 계약 확보 |

Node를 하나 추가할 때마다 POC라고 부르지 않는다. 위 이름은 서로 다른 기술적
불확실성을 검증하는 경계다.

## 목표 구조

### Routed Workflow v1

```text
START
  ↓
analyze_question
  ├─ law     → retrieve_law → generate_law ─┐
  ├─ product → search_products ─────────────┤
  ├─ mixed   → 위 두 조회를 병렬 실행 ─────┤→ compose → END
  ├─ clarify → ask_clarifying_question → END
  └─ out_of_scope → explain_scope → END
```

경로와 실행 순서를 코드가 정하므로 이 단계는 Agent가 아니라 Workflow다.

### Tool-calling Agent POC

```text
START → agent_model
            ├─ tool_calls 있음 → ToolNode → agent_model
            └─ tool_calls 없음 → END
```

모델이 Tool 사용 여부와 인자를 정하고 결과를 본 뒤 다시 선택하므로 이 단계부터
Agent라고 부른다.

## 최소 상태 계약

Routed Workflow에서 필요한 값만 단계별로 추가한다.

```text
question
route

law_question
articles
law_answer
law_error

product_filters
products
product_error

answer
```

- `route`: `law | product | mixed | clarify | out_of_scope`
- 법령과 상품 Node는 서로 다른 State 키를 사용
- 혼합 경로에서 예상 가능한 한쪽 오류는 상태에 남기고 다른 결과로 부분 답변
- Agent POC 전에는 `messages`와 메시지 Reducer를 추가하지 않음

## 구현 순서

### 1. 정기예금 1페이지 호출

- 목표: 은행권 정기예금 endpoint 정상 호출
- 파일: `src/chatbot/finlife.py`, `tests/test_finlife.py`
- 출력: Finlife 원본 `result`
- 검증: mock 정상 1건, HTTP 200·`err_cd != "000"` 1건, live smoke 1건
- 제외: 정규화, 적금, 페이지 순회, Graph, FastAPI

### 2. 정기예금 상품·옵션 정규화

- 목표: `baseList`와 `optionList`를 세 식별 키로 연결
- 출력: 프로젝트 내부 이름과 타입을 가진 상품 옵션
- 검증: 연결 성공 1건, 다른 키 옵션 제외 1건, `null` 보존
- 제외: 자연어 질문, 금리 순위, Node

내부 이름은 `company_name`, `product_name`, `term_months`,
`base_interest_rate`, `max_interest_rate`, `disclosure_month`를 사용한다.

### 3. 기간 필터·금리 정렬·후보 제한

- 목표: 기간과 정렬 기준으로 비교 후보 생성
- 입력: `term_months`, `sort_by`, `limit`
- 출력: 기본금리와 최고 우대금리를 모두 포함한 상위 후보
- 검증: 고정 fixture의 필터·정렬·상한
- 제외: LLM 추천 문장, live 응답을 평가 정답으로 사용

### 4. 적금 endpoint 계약 확인

- 목표: 적금 전용 필드와 정기예금 정규화의 공통 범위 확인
- 검증: mock 정상·본문 오류, live smoke 각 1건
- 결정: 확인 후에만 `product_type`을 가진 공통 조회 함수 검토
- 제외: 대출·보험·연금 상품

### 5. Product Node POC

- 목표: 정해진 상품 조건으로 `products`를 State에 추가
- 그래프: `START → search_products → END`
- 입력: 자연어가 아닌 검증된 상품 조건
- 검증: 상품 후보와 예상 가능한 `product_error` 상태
- 제외: 질문 분류, 법령 경로, 답변 생성

### 6. 고정 route 조건부 Edge

- 목표: State에 직접 넣은 `law` 또는 `product` 경로 선택
- 검증: 각 route가 지정 Node 한 곳만 실행
- 확인: Mermaid 문자열로 Graph 모양 확인
- 제외: LLM Router, 혼합 경로, Agent

### 7. 구조화 질문 분석 Node

- 목표: 자연어 질문을 route와 조회 입력으로 변환
- 출력: `route`, `law_question`, 상품 유형·기간·정렬 기준, 추가 질문
- 방식: Ollama Structured Output과 Python 값 검증
- 검증: 법령·상품·혼합·정보 부족·범위 밖 대표 사례
- 판단: 분류 정확성과 추가 latency를 함께 기록
- 제외: 최종 답변 생성과 Tool calling

### 8. 혼합 병렬 경로와 부분 실패

- 목표: 법령 검색과 상품 조회를 함께 실행해 합류
- 방식: 조건부 Edge가 혼합 질문에서 두 Node를 선택
- 상태: 두 Node가 서로 다른 키를 갱신하므로 별도 Reducer 미사용
- 검증: 양쪽 성공, 법령만 성공, 상품만 성공
- 주의: 예상 가능한 외부 오류만 Node에서 상태로 변환

### 9. Routed Workflow v1 답변 구성

- 목표: 모든 route가 사용자에게 표시할 `answer` 생성
- 법령: 현재 `answer_question()` 재사용
- 상품: 정규화 후보를 일정한 형식으로 렌더링
- 혼합: 법령 안내와 상품 후보를 `compose`에서 결합
- 검증: 근거·공시월·기본/우대금리 구분과 한쪽 실패 안내
- 제외: 새로운 복잡한 혼합 Prompt, Agent loop

### 10. Routed Workflow 비스트리밍 API

- 목표: 새 Workflow를 기존 법령 endpoint와 나란히 실행
- 응답: `response`, `route`, 법령 출처, 상품 출처, 시간, 부분 실패
- 검증: FastAPI 정상 1건과 중요한 실패 1건
- 유지: `/ask-rag`, `/ask-rag/stream`
- 제외: Streamlit 전환과 Agent 스트리밍

### 11. Qwen Tool call 단독 확인

- 목표: Graph 밖에서 Tool 이름과 JSON 인자 생성 확인
- 방식: 같은 로컬 Ollama와 Qwen을 `ChatOllama.bind_tools()`로 연결
- 순서: Tool 하나로 시작한 뒤 두 Tool 제공
- 검증: `AIMessage.tool_calls`의 이름·인자
- 제외: Agent loop와 FastAPI

이 단계에서만 `langchain-ollama` 의존성 추가 여부를 결정한다.

### 12. 두 Tool의 Agent loop

- Tool: `search_law_articles`, 검증된 상품 조회 Tool
- 상태: `MessagesState`
- 그래프: `agent_model ↔ ToolNode`, Tool 호출이 없으면 종료
- 안전장치: 이름 있는 실행 상한과 반복 Tool 사례
- 검증: 법령만, 상품만, 두 Tool, 추가 질문, Tool 오류
- 제외: persistence, memory, human-in-the-loop

Agent Tool은 생성된 법령 답변이 아니라 검색 조문과 정규화 상품을 반환한다. 최종
설명은 모델이 같은 실행의 Tool 결과를 사용해 작성한다.

### 13. Agent Dataset과 기준선

- 시점: Tool 이름·인자·message trace가 안정된 뒤
- 개발 Dataset: 32문항
- 빠른 확인: 같은 32문항 중 대표 12문항
- 유형: 법령 8, 상품 8, 혼합 8, 추가 질문·오류 8
- 평가: Tool 선택, 인자, 호출 집합·반복, 근거 일치, 최종 답변을 분리
- 재현성: 상품 Tool은 고정 fixture, live API는 연결 smoke만 사용

기존 24문항은 이 점수에 합치지 않고 법령 경로 회귀 평가로 유지한다.

### 14. Agent v1 비스트리밍 API

- 목표: 평가된 Agent Graph의 요청·응답 계약 연결
- 응답: 최종 답변, 사용 Tool, 법령·상품 출처, 종료·오류 정보
- 검증: 직접 Graph 실행 결과와 API 결과 일치
- 채택 판단: Routed Workflow v1보다 나은 점과 나쁜 점 비교
- 제외: 기존 RAG endpoint 교체

Agent POC가 느리거나 Tool 선택이 불안정하면 Routed Workflow v1을 기본 경로로
유지한다.

### 15. Agent 스트리밍과 Streamlit

- 목표: Tool 진행 상태와 최종 답변을 UI에서 구분
- 순서: 비스트리밍 계약 확인 후 별도 endpoint 추가
- 검증: Tool 호출 중 상태, 최종 답변 조각, 오류 종료
- 주의: 현재 RAG의 순수 텍스트 stream 계약을 바로 덮어쓰지 않음

## 이번 범위에서 사용하지 않는 기능

| 기능 | 보류 이유 |
| --- | --- |
| `Send` | 실행할 조회 경로가 법령·상품 두 개로 고정 |
| `Command` | 우선 조건부 Edge만으로 상태와 경로를 분리 가능 |
| Functional API | 현재 Graph API 학습·시각화 흐름 유지 |
| Subgraph | 기존 법령 Graph 중첩 시 State·streaming 복잡도 증가 |
| Checkpointer·Persistence | 첫 Agent는 단일 요청의 조회 전용 실행 |
| Short/Long-term Memory | 후속 질문을 같은 thread로 이어야 할 때 검토 |
| Interrupt·HITL | 가입·결제 같은 쓰기 Tool이 없음 |
| Plan-and-Execute | 두 조회 Tool에 비해 계획 비용이 큼 |
| Evaluator-Optimizer | 재생성 기준과 추가 모델 호출 필요성이 아직 없음 |
| Multi-Agent | 역할 분리보다 단일 Agent의 Tool 선택 검증이 먼저 |

## 공통 완료 규칙

- 각 단계는 가능한 한 하나의 커밋 단위로 유지
- 정상 1건과 중요한 실패 1건부터 검증
- 외부 상품 데이터 단위 테스트는 fixture 사용
- Graph 단계마다 실행된 Node와 State 결과 확인
- Graph 구조, Prompt, 검색 설정과 모델 설정을 동시에 변경하지 않음
- LangSmith·LangFeather에는 API 키와 원본 요청 URL을 남기지 않음

## 공식 참고

- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph Workflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangChain Tools와 ToolNode](https://docs.langchain.com/oss/python/langchain/tools)
- [LangChain ChatOllama](https://docs.langchain.com/oss/python/integrations/chat/ollama)
- [Ollama Tool Calling](https://docs.ollama.com/capabilities/tool-calling)
