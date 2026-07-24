# Finlife에서 LangGraph Agent까지 확장 명세

- 작성일: 2026-07-24
- 상태: 설계 초안, 지속 보완 예정
- 현재 기준선: Git `3dab94e`

## 이 문서의 결정

Agent Node를 늘리기 전에 법령 답변의 반복과 근거 밖 주장을 줄이는
`RAG prompt v2`를 별도 커밋으로 먼저 확인한다. 검색과 Graph 구조는 바꾸지 않고
prompt 한 변수만 비교한다.

그 다음 Finlife 관련 첫 구현은 은행권 정기예금 API를 한 번 호출하는 함수 하나로
시작한다. 법령 RAG, 상품 조회, 질문 분기와 tool calling을 한 번에 Agent로 묶지
않는다.

전체 방향은 다음과 같다.

```text
Finlife 계약 확인 완료
  → RAG prompt v2
  → 호출 함수
  → 응답 정규화
  → 상품 조회 Node
  → 법령·상품·혼합 조건 분기 workflow
  → 두 조회 기능을 read-only Tool로 전환
  → 모델이 Tool을 선택·반복하는 Agent
  → Agent 전용 Dataset과 기준선 평가
```

기존 24문항은 법령 RAG의 개발·회귀 Dataset으로 유지한다. Agent Dataset의 평가
계약과 대표 유형은 지금 설계하지만, 실제 JSONL 작성과 LangSmith 등록은 tool 이름,
인자와 첫 trajectory가 동작한 뒤 진행한다.

## 현재 기준선과 보존할 것

현재 `src/chatbot/graph.py`는 다음 선형 workflow를 실행한다.

```text
START → retrieve → generate → END
```

- `retrieve`는 `retrieve_articles()`로 법령 조문을 검색한다.
- `generate`는 `rag.py`의 LCEL `prompt | model | parser`를 재사용한다.
- 일반 응답과 스트리밍 모두 같은 compiled graph를 사용한다.
- `/ask-rag`와 `/ask-rag/stream`은 법령 전용 회귀 경로다.

LangChain과 LangGraph를 같은 24문항으로 비교했을 때 두 실행 모두 오류가 없었고
검색 `precision_top_5=0.280`, `recall_top_5=0.711`로 같았다. 따라서 Agent를
추가하면서 기존 graph를 즉시 교체하지 않는다.

보존 원칙:

- `create_rag_graph()`와 기존 두 endpoint를 법령 회귀 기준으로 유지
- 법령 XML snapshot, KURE-v1, Chroma와 top 5 설정 유지
- 기존 `rag-v1-dev` 24문항을 Agent 점수에 섞지 않음
- Finlife 기능이 안정되기 전 Streamlit 연결을 변경하지 않음
- 새 Agent endpoint가 필요해도 첫 API 호출 작업에는 추가하지 않음

## Finlife API 조사 결과

### 첫 POC 요청

2026-07-24에 다음 조건으로 공식 API를 직접 호출했다.

| 항목 | 값 |
| --- | --- |
| endpoint | `GET /finlifeapi/depositProductsSearch.json` |
| 권역 | `topFinGrpNo=020000` 은행 |
| 페이지 | `pageNo=1` |
| 인증 | `.env`의 `FINLIFE_API_KEY` |
| 결과 | HTTP 200, `err_cd=000`, `err_msg=정상` |
| 당시 건수 | 기본 상품 38건, 금리 옵션 152건 |

건수와 금리는 공시 시점에 따라 바뀌는 관찰값이다. 단위 테스트의 고정 기대값이나
제품 정책으로 사용하지 않는다.

### 응답 구조

최상위 `result` 안에 호출 결과와 두 목록이 있다.

```text
result
├── err_cd
├── err_msg
├── total_count
├── max_page_no
├── now_page_no
├── baseList
└── optionList
```

`baseList`에서 확인한 필드:

| 분류 | 필드 |
| --- | --- |
| 식별 | `dcls_month`, `fin_co_no`, `fin_prdt_cd` |
| 표시 | `kor_co_nm`, `fin_prdt_nm` |
| 가입 | `join_way`, `join_deny`, `join_member` |
| 조건 | `mtrt_int`, `spcl_cnd`, `etc_note`, `max_limit` |
| 공시 | `dcls_strt_day`, `dcls_end_day`, `fin_co_subm_day` |

`optionList`에서 확인한 필드:

| 분류 | 필드 |
| --- | --- |
| 식별 | `dcls_month`, `fin_co_no`, `fin_prdt_cd` |
| 기간 | `save_trm` |
| 금리 유형 | `intr_rate_type`, `intr_rate_type_nm` |
| 기본금리 | `intr_rate` |
| 최고 우대금리 | `intr_rate2` |

기본정보와 옵션은 다음 세 필드로 연결한다.

```text
(dcls_month, fin_co_no, fin_prdt_cd)
```

상품 코드만 연결하면 다른 공시월의 같은 상품을 잘못 합칠 수 있으므로 공시월을
제외하지 않는다.

Finlife 원본 필드명은 외부 API의 응답 계약이라 바꿀 수 없지만, 프로젝트 내부
이름까지 그대로 사용할 필요는 없다. 첫 호출 함수는 원본 계약을 확인하기 위해
`result`를 그대로 반환하고, 다음 정규화 함수에서 한 번만 변환한다.

| Finlife 원본 | 프로젝트 내부 이름 |
| --- | --- |
| `dcls_month` | `disclosure_month` |
| `fin_co_no` | `company_code` |
| `fin_prdt_cd` | `product_code` |
| `kor_co_nm` | `company_name` |
| `fin_prdt_nm` | `product_name` |
| `save_trm` | `term_months` |
| `intr_rate` | `base_interest_rate` |
| `intr_rate2` | `max_interest_rate` |

### 타입과 null

첫 응답에서 식별자·공시일·저축 기간은 문자열이었고, 금리는 정수 또는 실수 JSON
number였다. `max_limit`는 38건 중 23건, `dcls_end_day`는 30건에서 `null`이었다.
따라서 다음 원칙을 사용한다.

- 금리 비교 전 `float`로 정규화
- 원본 `save_trm`은 정규화 단계에서 정수 `term_months`로 변환
- Finlife 원본 필드명은 client 경계 밖으로 노출하지 않음
- `max_limit`와 `dcls_end_day`는 선택 값
- `null`을 0원이나 공시 종료로 해석하지 않음
- 알 수 없는 새 필드가 추가돼도 첫 POC의 필수 필드가 있으면 처리

### HTTP 성공과 API 성공의 차이

잘못된 권역코드로 요청했을 때 HTTP는 200이었지만 본문은 다음 값을 반환했다.

```text
err_cd=101
err_msg=topFinGrpNo의 부적절한 값
```

따라서 `raise_for_status()`만으로 성공을 판단할 수 없다. 구현은 다음 두 층을
구분해야 한다.

1. HTTP·timeout·JSON decode 실패
2. `result.err_cd != "000"`인 Finlife application 오류

인증키는 query parameter에 들어가지만 예외 문구, 로그, Tool 인자와 LangSmith
trace에는 남기지 않는다.

## 상품 답변의 범위

Finlife는 비교공시 데이터를 제공한다. 현재 프로젝트는 이를 개인화 추천이나 가입
판정이 아니라 **비교 후보 조회**로 사용한다.

답변 규칙:

- 기본금리와 최고 우대금리를 구분
- 최고 우대금리는 조건 충족 시 값이라고 표시
- 조회 기준일 또는 공시월 표시
- 가입 대상·제한·우대조건을 함께 확인하도록 안내
- API에 없는 예금자보호 여부를 상품 금리만으로 단정하지 않음
- 실제 가입 전 금융회사 공시와 상품설명서 재확인 안내
- 개인 상황을 받지 않은 상태에서 “가장 좋은 상품”으로 단정하지 않음

예를 들어 최고 우대금리가 가장 큰 상품은 정렬 결과 1위일 수 있지만, 사용자가
우대조건을 충족하지 못하면 실제 적용금리는 다를 수 있다. Agent와 endpoint의 용어도
`recommend`보다 `search`, `compare`, `candidates`를 우선한다.

## Workflow와 Agent를 구분하는 기준

질문을 분류해 코드에 정해진 Node로 보내는 것은 workflow다.

```text
START
  ↓
classify
  ├─ law     → retrieve_law
  ├─ product → search_products
  ├─ mixed   → retrieve_law + search_products
  └─ clarify → ask_clarifying_question
                   ↓
                 compose
                   ↓
                  END
```

이 구조도 LangGraph를 쓰는 의미가 있다. 상태, 조건부 Edge, 부분 실패와 두 결과의
합류를 명시할 수 있기 때문이다. 하지만 경로와 실행 순서를 코드가 고정하므로
tool-calling Agent라고 부르지는 않는다.

Agent v1은 모델이 Tool 호출 여부와 인자를 만들고, 결과를 본 뒤 다시 호출하거나
최종 답변을 선택하는 loop를 가진다.

```text
START → agent_model
            ├─ tool_calls 없음 → END
            └─ tool_calls 있음
                    ↓
                 ToolNode
                    ↓
                agent_model
```

LangGraph 공식 문서의 `ToolNode`와 `tools_condition`이 이 loop의 기본 형태다.
첫 Agent의 Tool은 모두 조회 전용이므로 승인·결제·가입 같은 쓰기 작업은 없다.

## 단계별 상태 설계

미래 필드를 현재 `RagState`에 한꺼번에 넣지 않는다.

| 단계 | 필요한 상태 | 넣지 않는 값 |
| --- | --- | --- |
| 현재 법령 graph | `question`, `articles`, `answer`, `streaming` | 상품·route·messages |
| 상품 Node POC | `question`, `products` | 대화 기록·재시도 횟수 |
| 조건 분기 workflow | `question`, `route`, 경로별 결과, `answer` | Agent message loop |
| tool-calling Agent | `messages`, Tool 결과를 확인할 최소 상태 | 장기 기억·사용자 프로필 |

혼합 질문에서 법령과 상품 Node가 서로 다른 키를 쓰면 결과 충돌 없이 합칠 수 있다.
오류도 한 문자열로 덮어쓰지 않고 어느 조회가 실패했는지 구분한다. 다만 구체적인
`TypedDict`는 해당 단계에서 실제로 사용하는 키만 추가한다.

## Tool 계약 초안

Tool 이름과 인자는 구현 중 한 번 검증한 뒤 Agent Dataset에 고정한다. 현재 초안은
다음 두 개다.

### `search_law_articles`

목적:

- 예금자보호, 설명의무, 소비자 권리의 법령 조문 검색

입력:

- 사용자 질문

출력:

- 법령명, 조문번호, 시행일, 본문을 가진 상위 조문

기존 `retrieve_articles()`를 감싸고 top 5 기준선을 먼저 유지한다. 기존
`/ask-rag`의 생성 답변 전체를 Tool 결과로 다시 넣기보다 근거 조문을 반환한다.
그래야 최종 Agent 답변을 실제 근거와 직접 비교할 수 있다.

### `search_financial_products`

목적:

- 현재 공시된 예·적금 비교 후보 조회

Agent에게 허용할 입력 후보:

- 상품 유형: 정기예금 또는 적금
- 금융 권역: 은행 또는 저축은행
- 저축 기간
- 기본금리 또는 최고 우대금리 기준
- 반환 후보 수

Agent에게 노출하지 않을 값:

- 인증키
- API host와 endpoint
- 임의 `pageNo`
- 원본 query parameter 이름

출력은 원본 전체 응답이 아니라 최대 후보 수만큼 정규화한 객체 목록이다. 상품명,
금융회사, 기간, 기본·최고 우대금리, 가입 제한, 우대조건, 공시월과 상품 식별자를
포함한다. 38개 상품과 152개 옵션 전체를 4,096 context에 넣지 않는다.

첫 POC에서는 이 일반 Tool을 만들지 않는다. 은행권 정기예금 1페이지 호출과 계약
검증부터 끝낸다. 적금 endpoint를 별도 호출해 공통점과 차이를 확인한 뒤에만
`product_type` 인자를 가진 하나의 Tool로 합친다.

## 모델 경계

현재 `OllamaGenerator`는 문자열 prompt를 `/api/chat`에 보내고
`message.content`만 반환한다. 요청에 `tools`가 없고 응답의 `tool_calls`도 보존하지
않으므로 지금 상태로는 Agent 모델 역할을 할 수 없다.

확인한 공식 지원:

- Qwen3-4B-Instruct-2507 모델 카드는 tool usage 향상을 명시
- Ollama `/api/chat`은 `tools` 요청과 `message.tool_calls` 응답 지원
- LangChain `ChatOllama`는 tool calling과 구조화 출력을 지원
- LangGraph `ToolNode`는 Tool 실행, `tools_condition`은 Tool 또는 종료 분기 지원

Agent 단계에서 우선 검토할 방법은 `langchain-ollama`의 `ChatOllama`를 model
인자로 graph에 주입하는 것이다. 이미 사용하는 LangGraph message·Tool 형식과 직접
연결할 수 있어 별도 JSON parser를 만들지 않아도 된다.

이 결정은 아직 의존성 추가 승인이 아니다. tool calling 한 건을 실제 Qwen3
quantized 모델로 확인하는 단계에서만 `uv add langchain-ollama`를 검토한다.
기존 문자열 `Generator`와 법령 LCEL 경계는 그대로 유지한다. Agent POC는 Ollama
backend만 지원하고 Hugging Face backend의 tool calling은 필요가 확인될 때 다룬다.

## 실패와 종료 정책

| 상황 | 기대 동작 |
| --- | --- |
| `FINLIFE_API_KEY` 없음 | 외부 호출 전 명확한 설정 오류 |
| HTTP timeout·연결 실패 | 상품 조회 불가를 상태에 남기고 키·전체 URL은 숨김 |
| HTTP 4xx·5xx | transport 오류로 처리 |
| 잘못된 JSON·필수 구조 없음 | upstream 응답 형식 오류 |
| `err_cd != "000"` | 코드와 안전한 메시지를 가진 Finlife 오류 |
| 조건에 맞는 상품 0건 | API 실패가 아닌 검색 결과 없음 |
| 혼합 질문에서 한 Tool만 실패 | 성공한 근거로 부분 답변하고 실패한 범위를 명시 |
| 같은 Tool 반복 호출 | 정해진 loop 상한에서 종료하고 한계를 안내 |
| 필요한 조건 부족 | 추측하지 않고 상품 유형·기간 등 한 가지 추가 질문 |

read-only 조회만 있으므로 첫 Agent에는 human-in-the-loop와 checkpointer를 넣지 않는다.
대화 기억, 재시도와 영속화도 실제 필요가 확인된 뒤 별도 작업으로 다룬다.

## Agent 평가 Dataset을 만드는 시점

### 판단

기존 생각처럼 **완성된 Agent Dataset의 생성·등록은 tool calling 이후**가 맞다.
다음 값은 구현 전에 정확히 알 수 없기 때문이다.

- 실제 Tool 이름과 JSON schema
- 모델이 만드는 인자 형태
- 단일·복수 Tool 호출 순서
- Graph trace에 남는 message와 Node 구조
- 오류가 ToolMessage로 전달되는 형식

하지만 평가 설계 전체를 그때 시작하면 늦다. 어떤 질문에서 어떤 Tool을 써야 하는지,
추가 질문이 필요한지, 무엇을 답하면 안 되는지는 구현 전에 정해야 한다. 그렇지 않으면
구현 결과에 맞춰 평가 기준을 사후 변경하게 된다.

따라서 세 시점으로 나눈다.

| 시점 | 할 일 | 현재 결정 |
| --- | --- | --- |
| 지금 | 질문 유형, 기대 Tool 집합, 금지 동작과 재현성 원칙 설계 | 이 문서에 기록 |
| 조건 분기·Tool 구현 중 | 각 작은 기능의 5~10개 사례를 단위 테스트 표로 검증 | 코드 단계에서 작성 |
| 두 Tool의 agent loop 후 | 로컬 `agent-v1-dev` JSONL 작성·검토·LangSmith 등록 | 아직 만들지 않음 |
| 첫 기준선 후 | 설정에 사용하지 않을 held-out test 추가 | 나중에 별도 버전 |

LangSmith 공식 가이드도 Agent를 최종 답변, single step, trajectory로 나누고 중요
구성요소마다 사람이 검토한 소수 예시부터 시작하도록 안내한다.

### 기존 24문항의 역할

`rag-v1-dev`는 다음 이유로 Agent 전체 평가에 그대로 사용할 수 없다.

- 입력이 법령 RAG 한 경로를 전제로 함
- 정답이 법령 조문과 Faithfulness 중심임
- 상품 Tool 이름·인자·호출 순서 정답이 없음
- D 유형은 상품 Tool이 없을 때 거절하는 동작을 정답으로 삼음
- Finlife 결과는 시간에 따라 바뀌지만 Dataset에는 상품 fixture 버전이 없음

그렇다고 버리지는 않는다.

- A·B·C 유형: `search_law_articles`와 기존 법령 subgraph의 회귀 평가
- D1·D2: Agent용 새 질문의 seed, 기대 동작은 상품 Tool 사용으로 다시 작성
- D3: 상품 존재 확인과 법령 한계가 함께 필요한 혼합 질문 seed
- E 유형: 일반 지식 경로를 만들 때까지 범위 밖 회귀 사례

질문 문장을 재사용하더라도 `rag-v1-dev`의 reference를 수정하지 않는다. 새 ID와
새 rubric을 가진 `agent-v1-dev`에 복사해 실험 의미를 분리한다.

### 첫 Agent dev set의 유형

16문항은 잘못된 분기처럼 큰 문제를 빠르게 찾는 용도로는 쓸 수 있지만, Agent의
전체 개발 기준선으로는 부족하다. 법령·상품·혼합·추가 질문 경로 안에서도 기간,
금리 기준, 두 Tool 조합과 실패 상황이 다시 나뉘기 때문이다.

첫 전체 개발 Dataset은 32문항으로 두고, 그중 대표적인 12문항을 자주 실행하는
빠른 확인용 묶음으로 사용한다. 빠른 확인용 12문항은 별도 질문이 아니라 전체
32문항의 부분집합이다.

| 유형 | 전체 개발 | 빠른 확인 | 기대 Tool 정책 |
| --- | ---: | ---: | --- |
| 법령 | 8 | 3 | 법령 Tool만 |
| 상품 | 8 | 3 | 상품 Tool만 |
| 혼합 | 8 | 3 | 두 Tool, 순서는 자유 |
| 추가 정보·오류 | 8 | 3 | 추가 질문 또는 안전한 부분 답변 |
| 합계 | 32 | 12 | 경로별 결과를 별도 점수로 기록 |

질문 하나의 실행 결과에서 Tool 선택, 인자, 호출 경로와 최종 답변을 함께 검사할 수
있으므로 평가 항목 수만큼 질문을 중복해서 만들지는 않는다. 기존 법령 RAG 24문항은
32문항과 섞지 않고 법령 검색·답변의 회귀 평가로 계속 사용한다. 첫 기준선 뒤에는
개발 중 보지 않은 12~20문항을 별도 평가용으로 추가한다.

### Dataset 필드 초안

```text
id
question
expected_tool_sets
argument_constraints
required_claims
forbidden_claims
expected_behavior
fixture_version
metric_eligibility
```

혼합 질문은 법령 다음 상품 또는 상품 다음 법령이 모두 맞을 수 있다.
따라서 `expected_tool_sets`는 가능한 Tool 집합과 순서 제약을 분리한다. 정확한
trajectory 하나만 강제하지 않는다.

### 평가 층

| 층 | 지표 또는 확인 | 방법 |
| --- | --- | --- |
| Finlife client | 응답 코드·필수 키·null 처리 | 단위 테스트 |
| 정규화 | base/option 연결, 기간 필터, 금리 정렬 | 결정적 코드 평가 |
| single step | 첫 Tool 선택, 인자 schema | exact code evaluator |
| trajectory | 필요한 Tool 포함, 불필요 호출·반복 없음 | unordered/subset 중심 |
| 법령 답변 | 검색 Precision·Recall, 근거 충실도 | 기존 evaluator 재사용·분리 |
| 상품 답변 | 언급 상품·금리가 실제 Tool 결과에 존재 | 결정적 grounding evaluator |
| 최종 답변 | 질문 충족, 제한·오류 안내 | rubric 기반 Judge와 사람 검토 |

최종 답변 점수 하나만 보면 잘못된 Tool을 호출하고도 그럴듯하게 답한 원인을 찾기
어렵다. 반대로 trajectory만 맞아도 금리나 법령을 잘못 옮길 수 있다. 두 층을 함께
보되 별도 feedback key로 기록한다.

### 동적인 상품 데이터의 재현성

offline Agent 평가는 매번 live Finlife API를 직접 호출하지 않는다.

이유:

- 공시 상품과 금리가 바뀌어 같은 답이 재현되지 않음
- 일일 호출 제한과 외부 장애가 모델 품질 점수에 섞임
- `max_page_no`와 상품 건수가 시점별로 달라짐

첫 Dataset은 실제 schema와 같은 작은 synthetic fixture를 Tool에 주입한다. 공시
원문 재배포 조건을 확인하기 전에는 live 전체 응답을 저장소에 커밋하지 않는다.
fixture에는 버전과 기준일을 기록한다.

별도로 live smoke test 한 건을 두어 공식 API 연결만 확인한다. live 실행의 상품명과
금리는 품질 기준선의 고정 reference로 쓰지 않고, 답변이 같은 실행의 Tool 결과만
인용했는지를 검사한다.

## 작은 구현 순서와 완료 기준

### 0. API 계약 조사 — 완료

새 개념:

- Finlife의 `baseList`·`optionList` 분리와 본문 오류코드

확인:

- 은행권 정기예금 정상 응답 1건
- 잘못된 권역코드 `err_cd=101` 1건

산출물:

- 이 명세와 외부 데이터 문서

### 선행 작업. RAG prompt v2 — 다음 작업

`src/chatbot/rag.py`의 prompt만 바꾸어 다음 두 동작을 확인한다.

- 직접 답하는 근거가 있으면 결론과 관련 조문만 제시
- 직접 답하는 근거가 없으면 관련 없는 조문을 나열하지 않고 확인 한계만 안내

정상 질문 한 건과 근거 부족 질문 한 건을 서버 UI에서 비교한다. 검색, Graph,
`top_k`, 생성 상한과 모델은 바꾸지 않는다.

### 1. 정기예금 1페이지 호출 함수

예상 파일:

- `src/chatbot/finlife.py`
- `tests/test_finlife.py`

입력:

- `api_key`
- 고정 기본값을 가진 은행 권역과 페이지

출력:

- Finlife `result` dict

검증:

- mock 정상 응답 1건
- HTTP 200 + `err_cd != "000"` 실패 1건
- 마지막에 live 정상 호출 1건

제외:

- Pydantic 도메인 모델
- 적금 endpoint
- 전체 페이지 순회
- 금리 정렬
- LangGraph와 FastAPI

### 2. 상품·옵션 정규화

세 키로 `baseList`와 `optionList`를 연결하는 함수 하나를 추가한다. `null`인
`max_limit`와 `dcls_end_day`를 그대로 보존한다. 12개월 옵션 한 상품의 연결과
연결 키가 다른 옵션 제외를 확인한다.

### 3. 조건 필터와 후보 제한

저축 기간 하나와 금리 기준 하나로 필터·정렬한다. 기본금리와 최고 우대금리를
동시에 반환하고, 결과 수 상한을 이름 있는 상수로 둔다. 아직 자연어 추천을 만들지
않는다.

### 4. 적금 endpoint 계약 확인

정기예금 함수와 분리해 은행권 적금 1페이지를 호출한다. `rsrv_type`처럼 적금에만
있는 필드와 null을 확인한 뒤 정규화 코드의 실제 공통 범위를 정한다. 정기예금
endpoint 이름을 억지로 일반화하지 않는다.

### 5. 상품 조회 Node

질문에서 분기하지 않고 정해진 상품 조건으로 Node 하나가 `products`를 상태에
추가하는지 확인한다. Finlife client와 Graph 개념을 동시에 새로 만들지 않기 위해
client가 검증된 뒤 연결한다.

### 6. 고정 route의 조건부 Edge

State에 주어진 `law` 또는 `product` 값에 따라 조건부 Edge 하나가 올바른 Node로
가는지만 확인한다. 아직 모델이 질문을 분류하지 않는다.

### 7. 질문 분류 Node

질문 한 건을 `law` 또는 `product`로 분류하는 최소 규칙 함수를 연결한다. 이 함수는
조건부 Edge와 실제 질문 입력을 확인하기 위한 임시 workflow 구성요소이며 Agent의
최종 의사결정기로 보지 않는다. 이 시점에 route 사례 5~10개를 작은 테스트 표로
만들고, Edge 구현과 분류 결과를 따로 확인한다.

### 8. 혼합·추가 정보 경로

`mixed`에서 두 결과를 모으고, `clarify`에서는 상품 유형이나 기간을 추측하지 않고
질문 하나를 반환한다. 한 Tool 실패 시 부분 답변 정책도 이 단계에서 확인한다.

### 9. Qwen3 tool call 한 건

법령 또는 상품 Tool 하나만 모델에 제공하고 올바른 Tool 이름과 JSON 인자가
나오는지 직접 확인한다. `ChatOllama` 의존성 추가는 이 단계에서만 결정한다.

### 10. 두 Tool의 Agent loop

`ToolNode`와 `tools_condition`으로 두 read-only Tool을 실행하고 모델로 돌아오는
loop를 만든다. 혼합 질문에서 두 Tool을 사용할 수 있게 하고 loop 상한을 둔다.

### 11. Agent dev Dataset과 기준선

실제 Tool schema와 trace를 기준으로 32문항 JSONL을 작성하고 사람이 검토한 뒤
LangSmith에 등록한다. 이 중 12문항에는 빠른 확인용 split을 부여한다. 한 단계의
선택, 전체 호출 경로, 근거 일치와 최종 답변을 분리해 평가한다.

### 12. FastAPI 연결

먼저 비스트리밍 Agent endpoint 한 개로 route, 답변, 법령·상품 source와 조회 기준을
확인한다. 스트리밍과 Streamlit 전환은 다음 작은 작업으로 분리한다.

### 13. Agent 이후 품질·성능 변경

Agent v1 기준선 뒤 다음 변경을 각각 별도 실험으로 진행한다.

- retrieval 또는 reranking 개선
- 출력 상한과 context 길이
- 첫 토큰·전체 응답·Ollama 세부 시간

구조, prompt, 검색과 모델 설정을 동시에 바꾸지 않는다.

## 기존 계획 문서와의 순서

| 문서 | 원래 결정 | 현재 해석 |
| --- | --- | --- |
| `docs/03-langsmith-evaluation/03-rag-baseline-workflow.md` | LangChain 기준선 뒤 같은 기능을 LangGraph로 비교 | 완료 |
| `docs/04-langgraph-migration/01-langgraph-migration-plan.md` | StateGraph 핵심, API, 24문항 재평가 뒤 상품 API | 완료 |
| `docs/04-langgraph-migration/03-what-langgraph-migration-means.md` | Finlife Node, 조건 분기, Tool 선택 Agent 순서 | 이 명세가 세분화 |
| `docs/05-performance-improvement/01-rag-latency-baseline-plan.md` | Agent 평가 뒤 성능 측정 | Agent v1 기준선 뒤 진행 |
| `docs/05-performance-improvement/03-rag-answer-repetition.md` | graph 기준선 뒤 prompt v2 | Agent Node 확장 전 다음 작업 |
| `docs/07-langgraph-agent/01-finlife-agent-expansion-spec.md` | 현재부터 Agent v1까지의 실행 계약 | 현재 기준 문서 |

문서 번호는 무조건 실행해야 하는 전역 순번이 아니라 주제별 기록 순서다. 서로 다른
시점의 “다음 작업”이 충돌할 때는 위 표와 이 명세의 작은 구현 순서를 따른다.

## 첫 Agent에서 하지 않는 것

- 상품 가입·해지·결제 같은 쓰기 Tool
- 투자·대출·보험까지 Finlife 범위 확대
- 사용자 자산을 이용한 개인화 추천
- 장기 기억과 사용자 프로필 저장
- checkpointer와 human-in-the-loop
- 다중 Agent와 subgraph hierarchy
- API 재시도·cache·주기적 전체 동기화
- 모든 backend를 위한 registry와 factory
- 현재 24문항 Dataset의 reference 덮어쓰기

필요가 관찰되기 전에 추가하지 않는다.

## 참고한 공식 자료

- [금융상품 한눈에](https://finlife.fss.or.kr)
- [Finlife 정기예금 API endpoint](https://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangChain Tools와 ToolNode](https://docs.langchain.com/oss/python/langchain/tools)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [LangChain ChatOllama](https://docs.langchain.com/oss/python/integrations/chat/ollama)
- [Qwen3-4B-Instruct-2507 모델 카드](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [LangSmith application-specific evaluation](https://docs.langchain.com/langsmith/evaluation-approaches)
- [LangSmith trajectory evaluation](https://docs.langchain.com/langsmith/trajectory-evals)
