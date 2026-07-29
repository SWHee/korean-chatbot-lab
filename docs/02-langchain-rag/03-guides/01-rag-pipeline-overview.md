# RAG 파이프라인 현재 구조

- 작성일: 2026-07-09

이 문서는 LangGraph로 넘어가기 전에 현재 RAG가 어디까지 구현되어 있는지 한 번
정리하기 위한 메모다. 자세한 실험 수치보다, 코드를 읽을 때 길을 잃지 않는 것을
목표로 한다.

## 전체 흐름

현재 RAG는 법령 원문을 검색 가능한 청크로 바꾼 뒤, 질문과 가까운 조문을 찾아
생성 모델에 함께 넣는 구조다.

```text
법령 XML
  → 조문 파싱
  → 조문 기반 청킹
  → KURE-v1 임베딩
  → Chroma 저장
  → 질문 임베딩
  → 관련 조문 검색
  → RAG 답변 생성
```

법령을 corpus로 선택한 이유는 구조가 비교적 분명하기 때문이다. 법률은 조문 번호,
시행일, 제목 같은 메타데이터가 있어서 검색 결과를 근거로 보여주기 쉽다. 예·적금
프로젝트에서는 상품을 추천하기 전에 보호 제도와 소비자 권리를 설명하는 역할도
분명하다.

## 인덱싱 워크플로우

| 순서 | 파일 | 역할 |
| --- | --- |
| 1 | `scripts/collect_laws.py` | 국가법령정보 Open API에서 법령 XML 원문 수집 |
| 2 | `data/laws/*.xml` | 수집된 법령 원문 snapshot |
| 3 | `src/chatbot/statutes.py` | XML에서 조문 단위 `Article` 추출 |
| 4 | `src/chatbot/chunking.py` | 조문 경계를 유지한 검색용 `Chunk` 생성 |
| 5 | `src/chatbot/embedding.py` | 청크 텍스트를 KURE-v1 1024차원 벡터로 변환 |
| 6 | `scripts/build_index.py` | 파싱·청킹·임베딩을 실행하고 Chroma에 저장 |

`build_index.py`는 일반 RAG 예제에서 말하는 `ingest.py`에 가까운 역할이다. 다만
현재 프로젝트는 새 문서만 조금씩 추가하기보다, 고정된 법령 snapshot 전체를 다시
인덱싱하는 방식을 사용한다.

## Retriever 워크플로우

| 순서 | 파일 | 역할 |
| --- | --- | --- |
| 1 | `src/chatbot/main.py` | `/ask-rag`, `/ask-rag/stream` 요청 수신 |
| 2 | `src/chatbot/embedding.py` | 사용자 질문을 KURE-v1 벡터로 변환 |
| 3 | `src/chatbot/vectorstore.py` | Chroma에서 질문과 가까운 청크 검색 |
| 4 | `src/chatbot/retriever.py` | 후보 청크를 조문 단위로 중복 제거 |
| 5 | `src/chatbot/rag.py` | 검색 조문을 prompt에 넣고 LCEL 체인으로 답변 생성 |

LangChain은 지금 단계에서 전체 구조를 대체하지 않는다. 기존에 만든 parser,
retriever, generator 경계를 유지하고, `rag.py`에서 prompt → model → parser 흐름을
작게 연결하는 데 사용한다. 결정 배경은
[`ADR 0007`](../01-adr/0007-integrate-langchain-with-minimal-lcel.md)에 기록한다.

### 왜 `StrOutputParser`를 쓰나

현재 RAG가 모델에서 받아야 하는 값은 사용자에게 보여 줄 한국어 답변 문자열이다.
그래서 LCEL 체인의 마지막에는 `StrOutputParser`를 둔다.

```text
ChatPromptTemplate → Generator를 감싼 RunnableLambda → StrOutputParser
```

지금의 `RunnableLambda`도 이미 문자열을 반환하므로 parser가 답변 형식을 크게
바꾸지는 않는다. 다만 prompt, model, parser의 역할을 코드와 LangSmith trace에서
구분할 수 있고, 나중에 후처리가 필요하면 마지막 단계만 바꿀 수 있다.

`with_structured_output()`은 정해진 항목으로 모델의 출력을 받아야 할 때 유용하다.
하지만 현재 Generator는 이 기능을 제공하는 LangChain ChatModel이 아니고, 최종
답변도 JSON보다 자연어가 알맞다. 출처와 응답 시간은 모델이 추측하게 하지 않고
FastAPI가 검색 결과와 측정값으로 직접 구성한다.

이후 LangGraph에서 질문 유형, 다음 경로, tool 호출 인자처럼 내부 판단을 정해진
형태로 받아야 할 때는 Pydantic 기반 structured output을 다시 검토한다.

## 보조 스크립트

| 파일 | 역할 |
| --- | --- |
| `scripts/verify_index.py` | 저장된 Chroma 검색 결과가 기준 검색 결과와 맞는지 확인 |
| `scripts/compare_embeddings.py` | 임베딩 모델 후보 비교용 실험 스크립트 |

Chroma 인덱스는 `data/index/` 아래에 만들어진다. 이 파일들은 코드로 다시 만들 수
있는 파생물이므로 Git에 올리지 않는다.

## 현재 API 역할

- `/ask-rag`: 법령 검색 후 답변과 출처를 JSON으로 반환
- `/ask-rag/stream`: 법령 검색 후 답변 텍스트를 조각으로 전송

RAG endpoint의 첫 요청은 일반 생성보다 느릴 수 있다. KURE-v1 임베딩 모델과
Chroma 컬렉션을 준비하는 비용이 있기 때문이다. 지금은 이 부분을 크게 최적화하기
보다, Next.js 화면에서 체감 동작을 확인한 뒤 필요한 부분만 개선한다.

## LangGraph로 넘어갈 때의 기준

현재 RAG는 단일 질문에 대해 검색하고 답하는 흐름까지 가능하다. LangGraph는 이
흐름을 무조건 바꾸기보다, 다음처럼 상태나 분기가 필요해질 때 도입하는 편이
자연스럽다.

- 법령 질문인지 상품 조회 질문인지 나누기
- 검색 근거가 부족하면 다른 단계로 넘기기
- 금융상품 한눈에 API 결과와 법령 RAG 답변을 함께 사용하기
- 사용자와 여러 턴을 이어가며 조건을 보충하기

즉, 지금의 RAG 코드는 LangGraph로 버리는 대상이 아니라, 이후 graph node로 감쌀 수
있는 재료에 가깝다.
