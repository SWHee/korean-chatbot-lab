# Finlife에서 멀티턴 LangGraph Agent까지의 실행 명세

- 최초 작성: 2026-07-24
- 최근 재정리: 2026-07-30
- 상태: 4단계 적금 endpoint 계약 확인 완료, 5단계 시작 전
- 현재 기준선: Git `aa40ed8`의 법령 RAG v2와 작업 트리의 예·적금 client·정기예금 비교

## 문서 역할

이 문서는 Finlife client부터 멀티턴 Agent v1까지의 **구현 순서와 단계별 완료
조건**만 관리한다. 작업을 시작할 때는 현재 단계 한 절만 우선 참고하고, 완료 조건을
확인한 뒤 다음 단계로 이동한다.

배경과 과거 결과는 다음 문서에 둔다.

- Finlife 응답 필드와 실제 호출 결과:
  [`외부 데이터와 API`](../06-other/01-external-data-sources.md)
- Agent 평가가 기존 24문항과 달라지는 이유:
  [`RAG 평가에서 Agent 평가로 넘어가기 전에 정리한 판단`](../03-langsmith-evaluation/12-agent-evaluation-research.md)
- 현재 법령 Graph와 LCEL의 역할:
  [`LangGraph로 마이그레이션한다는 의미`](../04-langgraph-migration/03-what-langgraph-migration-means.md)
- Agent 확장 전 생성 모델 전환 결정:
  [`Agent 확장 전 생성 모델 backend 전환 계획`](02-generation-model-backend-transition.md)

완료된 과거 계획과 이 문서의 미래 순서가 다르면 이 문서를 따른다.

## 제품 목표와 답변 경계

목표는 모델이 임의로 가장 좋은 상품 하나를 고르는 개인화 추천기가 아니다.

> 사용자의 모호한 요구를 대화로 구체화하고, Finlife 공시 데이터를 명시적인
> 기준으로 필터·정렬한 예·적금 비교 후보와 선택 이유를 안내하는 Agent

각 구성 요소의 책임을 다음처럼 고정한다.

| 구성 요소 | 책임 |
| --- | --- |
| Finlife client | 공시 상품과 기간별 금리 옵션 수집 |
| Python 비교 로직 | 정확한 조건 필터, 정렬, 후보 수 제한 |
| 질문 분석 | 질문 유형, 상품 조건, 부족한 조건 추출 |
| Agent model | 필요한 조회 Tool 선택과 결과 설명 |
| 법령 RAG | 보호한도, 설명의무, 소비자 권리의 일반 근거 안내 |

- `추천`은 **조건 기반 비교 후보 안내**라는 의미로만 사용
- 사용자가 정하지 않은 기준은 숨겨서 추측하지 않고 추가 질문하거나 기본 기준을 명시
- 기본 정렬이 필요하면 `base_interest_rate`, 기본 후보 수는 이름 있는 상수로
  정하고 답변에 비교 기준 표시
- 최고 우대금리가 가장 큰 상품을 개인에게 가장 유리한 상품으로 단정하지 않음
- Finlife 값은 실시간 시세가 아니라 조회 시점의 공시 정보로 표현
- 법령 RAG만으로 개별 상품의 예금자보호 여부를 판정하지 않음
- 상품 Vector DB, LLM 임의 점수, 협업 필터링은 필요성과 데이터가 확인되기 전 도입하지
  않음

## 질문 결과의 구분

`law`, `product`, `mixed`, `clarify`, `out_of_scope`는 다섯 개의 Node가 아니라
질문 분석 결과인 route 값이다.

| route·결과 | 의미 | 대표 동작 |
| --- | --- | --- |
| `law` | 법령 근거가 필요한 명확한 질문 | 법령 검색과 근거 답변 |
| `product` | 상품 비교가 필요한 명확한 질문 | Finlife 조회와 조건 비교 |
| `mixed` | 법령과 상품 정보가 모두 필요한 질문 | 두 조회를 병렬 실행한 뒤 결합 |
| `clarify` | 지원 범위 안이지만 대상이나 조건이 부족한 질문 | 가장 필요한 조건 하나를 질문 |
| `out_of_scope` | 현재 지원하지 않는 금융 주제 또는 비금융 질문 | 지원 범위를 짧게 안내 |
| `insufficient_evidence` | route는 명확하지만 검색 법령에 직접 근거가 없음 | 관련 없는 조문 없이 한계 안내 |

`insufficient_evidence`는 최초 route가 아니라 법령 검색 이후의 결과다. `clarify`도
거절이 아니라 다음 턴에서 비교 조건을 채우기 위한 정상 응답이다.

예를 들어 `"금융상품 추천해 주세요"`에는 예금·적금 중 무엇을 찾는지 묻고, 같은
thread의 다음 답변에서 기존 조건과 새 답변을 합친다. 비교할 수 있는 최소 조건이
확정되기 전에는 임의의 상품 하나를 가장 좋은 선택으로 단정하지 않는다.

## 현재 기준선과 유지할 계약

현재 법령 RAG는 다음 경로다.

```text
START → retrieve → generate → END
```

- `src/chatbot/graph.py`의 `create_rag_graph()`와 기존 RAG endpoint 유지
- 기존 법령 XML, KURE-v1, Chroma, 검색 상위 5개 설정 유지
- 생성 Node 안의 기존 LCEL과 Structured Output 재사용
- `rag-v1-dev` 24문항은 법령 경로의 회귀 평가로만 사용
- Finlife 인증키는 환경 변수에서만 읽고 State, Tool 인자, 로그, trace에서 제외
- 새 기능은 아래 순서에서 한 단계씩 구현하고 검증한 뒤 다음 단계로 이동

## 단계 이름

| 이름 | 검증할 불확실성 | 완료 기준 |
| --- | --- | --- |
| Finlife Client POC | 외부 API 호출과 응답 계약 | 고정 입력 정상·본문 오류 처리 |
| Product Node POC | 외부 조회를 Graph State에 연결 | 정규화 상품 후보와 오류 상태 |
| Routed Workflow POC | 코드가 정한 조건부 경로 | 법령·상품 분기와 혼합 합류 |
| Routed Workflow v1 | 단일 질문의 전체 응답 | 비스트리밍 API와 오류 계약 |
| Tool-calling Agent POC | 모델의 Tool 선택과 반복 | 단일·혼합 호출과 종료 |
| SQLite Persistence POC | thread별 상태 영속화 | 재연결 후 같은 대화 복원 |
| Multi-turn Clarify POC | 부족한 조건을 다음 턴에서 결합 | 두 턴 뒤 올바른 상품 조회 |
| Agent v1 | 평가 가능한 사용자 경로 | Dataset, trace, API, UI 계약 |

Node 하나를 추가할 때마다 POC라고 부르지 않는다. 위 이름은 서로 다른 기술적
불확실성을 처음 확인하는 경계다.

## 목표 구조

### Routed Workflow v1

```text
START
  ↓
analyze_question
  ├─ law     → retrieve_law → generate_law → END
  ├─ product → search_products → render_products → END
  ├─ mixed   ┬→ retrieve_law → generate_law ─────┐
  │           └→ search_products → render_products┴→ compose_mixed → END
  ├─ clarify → ask_clarifying_question → END
  └─ out_of_scope → explain_scope → END
```

혼합 경로의 두 Branch는 서로 다른 State 키를 갱신하고 합류한다. `compose_mixed`는
이미 생성된 법령 안내와 결정적으로 렌더링한 상품 후보를 결합하며, 같은 내용을 다시
생성하는 두 번째 LLM 호출을 기본값으로 두지 않는다.

경로와 실행 순서를 코드가 정하므로 이 단계는 Agent가 아니라 Workflow다.

### 단일 요청 Tool-calling Agent POC

```text
START → agent_model
            ├─ tool_calls 있음 → ToolNode → agent_model
            └─ tool_calls 없음 → END
```

모델이 Tool 사용 여부와 인자를 정하고 Tool 결과를 본 뒤 다음 행동을 선택하므로 이
단계부터 Agent라고 부른다.

### 멀티턴 Agent v1

```text
같은 thread_id

사용자 메시지
  ↓
analyze_turn
  ├─ clarify → 추가 질문 → END → checkpoint 저장
  ├─ out_of_scope → 범위 안내 → END → checkpoint 저장
  └─ ready → agent_model ↔ ToolNode → 최종 답변 → END → checkpoint 저장

다음 사용자 메시지
  → 같은 thread의 messages·product_preferences 복원
  → analyze_turn부터 새 실행
```

일반 채팅의 추가 질문은 `interrupt()`로 한 실행을 정지하지 않는다. 매 턴을 정상
종료하고 같은 `thread_id`로 다음 요청을 실행한다.

## 상태와 Tool 계약

### Routed Workflow State

```text
question
route

law_question
articles
law_answer
law_status

product_filters
products
product_answer
product_status

clarifying_question
answer
```

- `law_status`: `ok | insufficient_evidence | error`
- `product_status`: `ok | no_match | error`
- 법령과 상품 Branch는 서로 다른 키를 갱신
- 예상 가능한 한쪽 오류는 상태에 남기고 혼합 답변은 성공한 결과로 부분 구성

### Agent State

Tool Agent부터 `MessagesState`를 사용하고, 멀티턴 단계에서 다음 값을 추가한다.

```text
messages                 # add_messages Reducer로 누적
product_preferences      # 확정된 구조화 상품 조건
missing_fields           # 다음 턴에서 받을 조건
route
```

최소 상품 조건은 다음 범위에서 시작한다.

```text
product_type             # deposit | saving
term_months
sort_by                  # base_interest_rate | max_interest_rate
limit
```

- `thread_id`와 SQLite 경로는 State가 아니라 runtime config
- API 키와 backend 객체는 State에 저장하지 않음
- 메시지만 다시 읽어 매번 조건을 추측하지 않고 확정된 조건을 구조화 State로 유지
- 부분 조건 갱신 시 기존 조건을 잃지 않도록 전체 모델 교체 또는 명시적인 병합 규칙
  사용

### Agent Tool

처음 바인딩할 Tool은 두 개다.

| Tool | 모델 입력 | 반환 |
| --- | --- | --- |
| `search_law_articles` | 법령 검색 질문 | 근거 ID, 법령명, 조문번호, 시행일, 조문 |
| `search_financial_products` | 상품 유형, 기간, 정렬 기준, 후보 수 | 정규화 상품, 기본·최고금리, 공시월, 비교 기준 |

- Tool은 최종 답변이 아니라 근거 데이터를 반환
- Finlife 인증키, 권역 기본값, pagination은 Tool 내부에서 처리
- Agent model은 원본 전체 JSON이나 Finlife 약어 필드를 받지 않음
- 상품 순위는 Tool 내부 Python 로직이 정하고 모델은 순서를 임의로 바꾸지 않음

## 구현 순서

### 1. 정기예금 1페이지 호출

- 상태: 완료 (2026-07-30)
- 목표: 은행권 정기예금 endpoint 정상 호출
- 파일: `src/chatbot/finlife.py`, `tests/test_finlife.py`
- 출력: Finlife 원본 `result`
- 검증: mock 정상 1건, HTTP 200·`err_cd != "000"` 1건, live smoke 1건
- 결과: mock 2건과 실제 API smoke 통과, 전체 pytest 회귀 없음
- 제외: 정규화, 적금, 페이지 순회, Graph, FastAPI

### 2. 정기예금 상품·옵션 정규화

- 상태: 완료 (2026-07-30)
- 목표: `baseList`와 `optionList`를 세 식별 키로 연결
- 출력: 프로젝트 내부 이름과 타입을 가진 상품 옵션
- 검증: 연결 성공 1건, 다른 키 옵션 제외 1건, `null` 보존
- 결과: 고정 데이터 2건과 실제 API 정규화 smoke 통과
- 제외: 자연어 질문, 금리 순위, Node

내부 이름은 `company_name`, `product_name`, `term_months`,
`base_interest_rate`, `max_interest_rate`, `disclosure_month`를 사용한다.

### 3. 기간 필터·비교 기준 정렬·후보 제한

- 상태: 완료 (2026-07-30)
- 목표: 정확한 기간과 명시적인 정렬 기준으로 비교 후보 생성
- 입력: `term_months`, `sort_by`, `limit`
- 출력: 기본·최고금리와 `comparison_basis`를 가진 상위 후보
- 기본: 기본금리 우선과 후보 3개를 이름 있는 상수로 두고 적용 사실 표시
- 검증: 고정 fixture의 필터·정렬·동률·상한
- 결과: 기본·최고금리 기준, 미공시 금리 제외, 동률 순서, 입력 오류 검증 통과
- 제외: LLM 순위 결정, 우대조건 의미 검색, live 응답을 평가 정답으로 사용

### 4. 적금 endpoint 계약 확인

- 상태: 완료 (2026-07-30)
- 목표: 적금 전용 필드와 정기예금 정규화의 공통 범위 확인
- 검증: mock 정상·본문 오류, live smoke 각 1건
- 결정: 확인 후에만 `product_type`을 가진 공통 조회 함수 도입
- 결과: 기본정보는 공통이고 적금 옵션에 `rsrv_type`, `rsrv_type_nm` 추가 확인
- 적용: HTTP 호출·오류 처리는 공통화하고 적금 정규화는 다음 결정 전까지 분리
- 제외: 대출·보험·연금 상품

### 5. Product Node POC

- 목표: 검증된 상품 조건으로 `products`와 `product_status`를 State에 추가
- 그래프: `START → search_products → END`
- 입력: 자연어가 아닌 구조화 상품 조건
- 검증: 상품 후보, 결과 없음, 예상 가능한 API 오류
- 제외: 질문 분류, 법령 경로, 답변 생성

### 6. 고정 route 조건부 Edge

- 목표: State에 직접 넣은 `law` 또는 `product` 경로 선택
- 검증: 각 route가 지정 Node 한 곳만 실행
- 확인: Mermaid 문자열로 Graph 모양 확인
- 제외: LLM Router, 혼합 경로, Agent

### 7. 구조화 질문 분석 Node

- 목표: 자연어 질문을 route와 조회 입력으로 변환
- 출력: `route`, `law_question`, `product_filters`, `missing_fields`,
  `clarifying_question`
- 방식: 선택한 API 모델의 Structured Output과 Python 값 검증
- 검증: 법령·상품·혼합·조건 부족·범위 밖 대표 사례
- 구분: 검색 후 근거 부족은 `clarify`가 아니라 `insufficient_evidence`
- 판단: 분류 정확성과 추가 latency를 함께 기록
- 제외: 이전 턴 기억, Tool calling, 최종 답변

### 8. 혼합 병렬 경로와 부분 실패

- 목표: 법령과 상품 Branch를 병렬 실행한 뒤 합류
- 상태: 두 Branch가 서로 다른 키를 갱신하므로 별도 Reducer 미사용
- 검증: 양쪽 성공, 법령만 성공, 상품만 성공
- 주의: 예상 가능한 외부 오류만 Node에서 상태로 변환
- 제외: Agent의 동적 Tool 선택

### 9. Routed Workflow v1 답변 구성

- 목표: 모든 route가 사용자에게 표시할 `answer` 생성
- 법령: 현재 `answer_question()` 재사용
- 상품: 후보 순서, 비교 기준, 공시월, 기본·최고금리를 일정한 형식으로 렌더링
- 혼합: 두 완성 섹션을 추가 LLM 호출 없이 결합
- clarify: 한 번에 가장 중요한 조건 하나를 쉬운 선택지와 함께 질문
- out-of-scope: 현재 지원 범위와 다시 물을 수 있는 예시 안내
- 검증: 정상, 근거 부족, 결과 없음, 한쪽 실패

### 10. Routed Workflow 비스트리밍 API

- 목표: 새 Workflow를 기존 법령 endpoint와 나란히 실행
- 응답: 답변, route, 상태, 법령·상품 출처, 시간, 부분 실패
- 검증: FastAPI 정상 1건과 중요한 실패 1건
- 유지: `/ask-rag`, `/ask-rag/stream`
- 제외: thread, Next.js 연결, Agent 스트리밍

### 11. 선택한 모델의 Tool call 단독 확인

- 목표: Graph 밖에서 Tool 이름과 JSON 인자 생성 확인
- 방식: 현재 기본 API backend의 LangChain ChatModel에 `bind_tools()` 적용
- 순서: 법령 Tool 하나로 시작한 뒤 두 Tool 제공
- 검증: `AIMessage.tool_calls`의 이름·인자와 Tool 불필요 질문
- 제외: Agent loop와 FastAPI

Ollama Tool Calling은 오픈웨이트 LoRA·vLLM 실습 결과를 다시 연결할 때 별도 비교한다.

### 12. 두 Tool의 단일 요청 Agent loop

- Tool: `search_law_articles`, `search_financial_products`
- 상태: `MessagesState`
- 그래프: `agent_model ↔ ToolNode`, Tool 호출이 없으면 종료
- 안전장치: 이름 있는 실행 상한, 동일 Tool·인자 반복 감지
- 검증: 법령만, 상품만, 두 Tool, Tool 불필요, Tool 오류
- 제외: Checkpointer, 이전 요청 기억, FastAPI

Agent Tool은 생성된 답변이 아니라 검색 조문과 정규화 상품을 반환한다. 최종 설명은
모델이 같은 실행의 Tool 결과만 사용해 작성한다.

### 13. SQLite Checkpointer POC

- 목표: 같은 thread 상태를 서버 메모리가 아닌 SQLite에 저장·복원
- 의존성: 필요 시 `langgraph-checkpoint-sqlite` 추가
- 저장 위치: 저장소에서 제외할 `/.runtime/langgraph.sqlite3`
- 설정: `thread_id`는 runtime config로 전달
- 검증: 같은 thread 복원, 다른 thread 격리, DB 연결 재생성 후 복원
- 보안: 메시지·상품 조건만 저장하고 API 키와 backend 객체 제외
- 제외: 상품 추가 질문, FastAPI, UI, Time Travel 화면

Docker 배포에서 이 파일을 유지할 때는 컨테이너 내부 경로만 사용하지 않고 별도
volume을 연결한다. Compose 수정과 재생성 검증은 실제 Agent 배포 단계 문서에서
다룬다.

### 14. 멀티턴 Clarify POC

- 목표: 모호한 첫 질문과 다음 답변을 같은 thread에서 합쳐 상품 조회
- 상태: `messages`, `product_preferences`, `missing_fields`
- 분석: 7단계 질문 분석을 현재 턴과 기존 상품 조건을 병합하도록 확장
- 흐름: 추가 질문을 반환하고 END한 뒤 다음 요청에서 같은 thread로 재실행
- 기본 정책: 필수 조건 하나씩 질문하고 숨은 조건을 추측하지 않음
- 검증: `"금융상품 추천"` → 상품 유형 질문 → `"적금, 12개월"` → 상품 Tool 호출
- 추가 검증: 새 thread에는 이전 조건이 섞이지 않음
- 제외: `interrupt`, 장기 사용자 프로필, 민감한 소득·자산 수집, UI

### 15. Agent Dataset과 기준선

- 시점: Tool schema, 반복 종료, SQLite thread, 두 턴 조건 병합이 안정된 뒤
- 개발 Dataset: 32사례
- 빠른 확인: 같은 Dataset 중 대표 12사례
- 구성: 법령 8, 상품 8, 혼합 8, 근거 부족·범위 밖·오류 8
- 멀티턴: 상품·혼합에서 각 4사례, 총 8개를 두 턴 trajectory로 구성
- clarify 평가: 첫 추가 질문과 다음 답변 이후 조건 병합을 하나의 실행 단위로 평가
- 평가: Tool 선택, 인자, 호출 집합·반복, 조건 기억, 근거 일치, 최종 답변 분리
- 재현성: 상품 Tool은 고정 fixture, live API는 연결 smoke만 사용

기존 24문항은 Agent 점수에 합치지 않고 법령 경로 회귀 평가로 유지한다. 결정적인
Tool·인자·상품 값은 코드로 평가하고, 문장 도움 정도만 Judge와 사람 검토를 사용한다.

### 16. Agent v1 비스트리밍 API

- 목표: 평가된 Agent Graph를 기존 RAG endpoint와 분리해 연결
- 요청: `thread_id`, 현재 사용자 메시지
- 응답: thread, 대화 상태, 최종·추가 질문, 사용 Tool, 출처, 종료·오류 정보
- 검증: 첫 질문과 같은 thread의 후속 답변, 새 thread 격리
- 유지: 기존 RAG와 Routed Workflow endpoint
- 제외: 기존 endpoint 교체, 스트리밍, SQLite 관리 UI

Agent가 느리거나 Tool 선택이 불안정하면 Routed Workflow v1을 기본 상품 경로로
유지하고 비교 결과를 기록한다.

### 17. Agent 이벤트 스트리밍 API

- 목표: 진행 상태와 최종 답변 조각을 구분한 별도 stream 계약
- 이벤트: `status`, `token`, `result`, `error`
- 상태 예시: 질문 분석, 법령 검색, 상품 조회, 답변 생성
- LangGraph 모드: 필요에 따라 `updates`, `messages`, `custom` 조합
- 검증: Tool 진행 상태, 최종 답변 조각, 추가 질문, 오류 종료
- 주의: 현재 RAG의 순수 텍스트 stream 계약을 덮어쓰지 않음

### 18. Next.js 멀티턴 Agent UI

- 목표: 같은 thread의 추가 질문과 Tool 진행 상태를 사용자에게 표시
- thread: 새 대화에서 ID 생성, 후속 메시지에서 재사용
- UI: 추가 질문, 비교 기준, 상품 후보, 법령 출처, 진행 상태 구분
- 검증: 모호한 질문부터 두 턴 이상 진행해 후보 확인, 새 대화 격리
- 제외: Time Travel UI, 장기 사용자 프로필, 가입·결제 동작

## 이번 범위의 LangGraph 개념

| 개념 | 적용 시점과 역할 |
| --- | --- |
| StateGraph·Node·Edge | 전체 단계의 상태와 실행 순서 |
| Conditional Edge | law·product·mixed·clarify·out-of-scope 분기 |
| Parallelization | mixed의 법령·상품 Branch |
| Structured Output | route, 상품 조건, 부족한 조건 검증 |
| Tool Calling·ToolNode | 모델의 조회 선택과 결과 반환 |
| MessagesState·Reducer | 대화와 Tool 메시지 누적 |
| Loop·Termination | Agent model과 ToolNode 반복 상한 |
| Checkpointer·Thread·Checkpoint | SQLite 기반 턴 간 단기 기억 |
| Short-term Memory | 같은 thread의 메시지와 상품 조건 유지 |
| Streaming | Node 진행 상태와 최종 토큰 구분 |

Checkpointer 도입으로 장애 복구와 Time Travel의 기반은 생기지만, 기능을 한꺼번에
구현하지 않는다. replay에서는 이후 LLM과 API 호출이 다시 실행될 수 있으므로
읽기 Tool을 유지하고, 평가 상품은 fixture로 고정한다.

## 이번 범위에서 보류하는 기능

| 기능 | 보류 이유 |
| --- | --- |
| `Send` | 실행할 조회 Branch가 법령·상품 두 개로 고정 |
| `Command` | 일반 추가 질문은 매 턴 END하고 새 입력으로 재실행 |
| Functional API | 현재 Graph API 학습·시각화 흐름 유지 |
| Subgraph | 기존 법령 Graph 중첩보다 Node 함수 재사용이 단순 |
| Interrupt·HITL | 가입·결제·승인 같은 쓰기 Tool이 없음 |
| Time Travel UI | Checkpointer 확인 뒤 디버깅 필요가 생길 때 검토 |
| Long-term Memory·Store | 다른 thread까지 사용자 성향을 기억하지 않음 |
| Plan-and-Execute | 두 조회 Tool에 비해 계획 비용이 큼 |
| Evaluator-Optimizer | 재생성 기준과 추가 모델 호출 필요성이 아직 없음 |
| Multi-Agent | 단일 Agent의 Tool 선택과 멀티턴 검증이 먼저 |
| 상품 Vector DB | 숫자·기간 필터는 구조화 비교가 더 정확 |

## 공통 완료 규칙

- 각 단계는 가능한 한 하나의 커밋 단위로 유지
- 정상 1건과 중요한 실패 1건부터 검증
- 외부 상품 데이터 단위 테스트와 Agent 평가는 고정 fixture 사용
- Graph 단계마다 실행 Node, State 갱신, 종료 이유 확인
- Graph 구조, Prompt, 검색 설정, 모델 설정을 동시에 변경하지 않음
- 기본값과 정렬 기준은 이름 있는 상수로 두고 사용자 답변에 표시
- API 키와 SQLite 파일은 저장소에 포함하지 않음
- 추천에 불필요한 소득·자산 정보는 요구하지 않고 trace의 사용자 입력 보관 범위를
  Agent API 연결 전에 다시 검토
- Finlife 조회 Tool은 읽기 전용으로 유지
- 체크포인트 replay와 재시도에서 같은 읽기 호출이 반복될 수 있음을 고려
- LangSmith·LangFeather에는 API 키와 원본 인증 URL을 남기지 않음

## 공식 참고

- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph Workflows and Agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Memory](https://docs.langchain.com/oss/python/langgraph/add-memory)
- [LangGraph Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Time Travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
- [LangChain Tools와 ToolNode](https://docs.langchain.com/oss/python/langchain/tools)
- [LangChain ChatOllama](https://docs.langchain.com/oss/python/integrations/chat/ollama)
- [Ollama Tool Calling](https://docs.ollama.com/capabilities/tool-calling)
