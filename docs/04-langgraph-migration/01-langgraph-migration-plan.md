# LangGraph 전환 계획

- 작성일: 2026-07-20

현재 LangChain RAG는 질문 검색, 문맥 구성, 답변 생성과 FastAPI 연결까지 동작한다.
첫 LangGraph 작업은 기능을 늘리는 것이 아니라 이 흐름을 `StateGraph`로 옮기고,
LangChain v1 기준선과 같은 동작을 하는지 확인하는 것이다.

## 첫 전환에서 바꾸지 않는 것

- 법령 XML과 Chroma 인덱스
- KURE-v1 질문 임베딩
- 조문 단위 top 5 검색
- 현재 RAG prompt
- Ollama Qwen3 생성 모델
- FastAPI의 기존 `/ask-rag` 경로
- Dataset과 Gemini Judge

한 번에 여러 요소를 바꾸지 않아야 결과 차이가 graph 구조 때문인지 설명할 수 있다.
상품 API와 질문 분기는 구조 전환을 검증한 뒤 추가한다.

## 최소 graph의 상태

처음에는 질문 한 건을 처리하는 데 필요한 값만 상태로 둔다.

```text
question  사용자 질문
articles  검색된 조문 목록
answer    생성 답변
sources   API에 표시할 법령 출처
```

대화 기록, 재시도 횟수, 상품 후보처럼 아직 사용하지 않는 값은 미리 넣지 않는다.

## 작은 작업 순서

### 1. 상태와 검색 node

새 개념은 `StateGraph`의 상태와 node 하나다. 검색 node는 기존
`retrieve_articles()`를 호출하고 `articles`만 상태에 추가한다.

확인할 동작은 질문을 넣었을 때 기존 retriever와 같은 조문이 나오는지 한 건 비교하는
것이다. 이 단계에서는 답변을 만들거나 endpoint를 추가하지 않는다.

### 2. 답변 생성 node와 graph 연결

생성 node는 기존 `answer_question()`을 사용해 `answer`와 `sources`를 만든다.

```text
START → retrieve → generate → END
```

LCEL prompt와 Generator 경계는 그대로 재사용한다. LangGraph 안에서 검색·생성
기능을 다시 구현하지 않는다.

### 3. graph 한 건 실행

고정 질문 A1로 graph를 직접 실행하고 다음 항목을 기존 LangChain 실행과 비교한다.

- 검색 조문 ID
- prompt에 들어간 문맥
- 답변과 출처 구조
- LangSmith trace에서 보이는 node 순서

생성 문장은 실행마다 달라질 수 있으므로 문자열 완전 일치를 요구하지 않는다.

### 4. FastAPI 비교 경로

graph 실행이 확인된 뒤에만 비교용 endpoint를 하나 추가한다. 기존 `/ask-rag`는
LangChain v1 기준으로 유지해 두고, 임시 graph 경로에서 같은 요청·응답 형식을
사용한다. 비교가 끝난 뒤 어느 경로를 기본으로 둘지 결정한다.

### 5. 같은 Dataset 재평가

`rag-v1-dev` 24문항과 기존 evaluator를 그대로 사용한다. LangChain v1의 단일 24문항
기준선과 같은 조건으로 실행하면 문항별 변화를 바로 비교할 수 있다.

구조만 옮긴 단계에서는 점수 상승보다 다음 조건이 중요하다.

- 질문 누락과 실행 오류가 없음
- 검색 Precision·Recall이 유지됨
- Faithfulness가 크게 나빠진 문항이 없음
- graph trace에서 검색과 생성 node를 구분할 수 있음

## 구조 전환 다음 단계

기본 graph가 같은 동작을 하는 것을 확인한 뒤 금융상품 한눈에 API를 추가한다.

```text
사용자 질문
  → 질문 유형 판단
  ├─ 법령 질문 → 법령 retriever
  ├─ 상품 탐색 → Finlife API
  └─ 혼합 질문 → 두 결과를 함께 사용
```

이때부터 LangGraph를 쓰는 이유가 분명해진다. 질문에 따라 경로를 고르고, API 실패 시
다른 안내로 이동하며, 여러 결과를 하나의 상태에 모을 수 있기 때문이다. 멀티턴 상태와
Agent 도구 선택은 이 분기가 실제로 동작한 뒤 별도 단계에서 검토한다.
