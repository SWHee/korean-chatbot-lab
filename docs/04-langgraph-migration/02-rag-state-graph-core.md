# RAG StateGraph 핵심 구현

- 작성일: 2026-07-22

기존 법령 RAG의 검색과 생성을 바꾸지 않고 실행 순서만 LangGraph로 옮겼습니다.
FastAPI나 평가에 연결하기 전에 Graph 자체가 동작하는지 확인하는 단계입니다.

## 상태와 실행 흐름

Graph의 상태에는 질문 처리 과정에서 만들어지는 값만 둡니다.

| 키 | 역할 |
| --- | --- |
| `question` | 사용자가 입력한 질문 |
| `articles` | 검색된 법령 조문 |
| `answer` | 법령 근거로 생성한 답변 |

실행 순서는 다음과 같습니다.

```text
START → retrieve → generate → END
```

- `retrieve`는 기존 `retrieve_articles()`를 호출해 `articles`를 추가합니다.
- `generate`는 기존 `answer_question()`을 호출해 `answer`를 추가합니다.
- 임베딩, Chroma 검색, LCEL prompt와 Ollama 생성 코드는 다시 작성하지 않았습니다.

## Graph 생성 함수

`create_rag_graph()`는 FastAPI나 테스트가 전달한 `generator`, `encoder`,
`collection`을 각 Node에 연결하고 실행 가능한 Graph를 반환합니다. 모델과 DB 객체는
질문 처리 결과가 아니므로 State에는 넣지 않습니다.

이 구조로 실제 서버에서는 기존 RAG 자원을 사용하고, 단위 테스트에서는 가짜 자원을
전달할 수 있습니다.

## 확인한 동작

가짜 검색과 생성 함수를 사용한 단위 테스트에서 다음 순서를 확인했습니다.

1. 질문이 Graph에 입력됨
2. `retrieve`가 법령 조문을 State에 저장
3. `generate`가 질문과 조문을 받아 답변 생성
4. 최종 State에 `question`, `articles`, `answer`가 모두 존재

실제 KURE-v1, Chroma, Ollama는 이 테스트에서 적재하지 않습니다. 이 단계의 목적은
모델 품질이 아니라 Graph의 상태 전달과 Node 실행 순서를 검증하는 것입니다.

## 아직 연결하지 않은 부분

- FastAPI `/ask-rag`
- `/ask-rag/stream` 토큰 스트리밍
- LangSmith 평가 target
- Finlife API와 조건 분기

이 항목은 Graph 핵심 동작을 확인한 뒤 각각 작은 작업으로 연결합니다.
