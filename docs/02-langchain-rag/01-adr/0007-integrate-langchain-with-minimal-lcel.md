# ADR 0007. 기존 경계를 유지하며 최소 LCEL 체인으로 LangChain을 연결한다

- 상태: Accepted
- 결정일: 2026-07-08
- 기록 보완일: 2026-07-21
- 구현 상태: Implemented

## 배경

법령 파싱, 청킹, 임베딩, Chroma 검색과 Ollama 생성이 각각 동작한 뒤 LangChain 기반
RAG로 연결할 단계가 됐다. 이미 프로젝트가 직접 소유하는 `Generator`, retriever와
vectorstore 경계가 있었으므로, LangChain을 배우기 위해 검증된 코드를 전부 교체할
필요는 없었다.

사용자는 교재에서 `prompt | model | parser` 형태의 LCEL 체인을 먼저 접했다. 초기
연결 코드에 lambda 표현과 여러 처리가 한곳에 섞이자 체인이 어디에서 만들어지고
실행되는지 알아보기 어렵다는 문제가 있었다. 프레임워크를 많이 사용하는 것보다 각
단계의 역할을 직접 설명할 수 있는 구조가 더 중요했다.

## 고려한 선택지

1. 기존 함수를 유지하고 LangChain을 사용하지 않는다.
2. retriever, Chroma, Ollama 생성기를 LangChain 구현체로 모두 교체한다.
3. 기존 경계를 유지하고 필요한 부분만 Runnable로 감싸 LCEL 체인을 만든다.

첫 번째는 기존 RAG를 실행할 수 있지만 LangChain의 prompt, Runnable, parser와 trace
흐름을 학습하기 어렵다. 두 번째는 코드 교체 범위가 크고, 동작이 달라졌을 때 원인을
찾기 어렵다. 현재 POC에서는 세 번째 선택지가 가장 작은 변경으로 학습 목표를
충족한다.

## 결정

기존 RAG 구성요소를 유지하고 생성 단계만 최소 LCEL 체인으로 연결한다.

```text
ChatPromptTemplate
  → RunnableLambda로 감싼 Generator
  → StrOutputParser
```

- `Generator`는 Ollama나 Hugging Face 세부 구현을 숨기는 프로젝트 경계로 유지한다.
- 검색은 기존 `retrieve_articles()`와 Chroma 경계를 그대로 사용한다.
- `RunnableLambda`는 일반 함수인 `generator.generate()`를 LCEL에서 실행할 수 있게
  연결하는 adapter 역할만 맡는다.
- lambda 식을 체인 안에 바로 쓰지 않고 `create_model_runnable()`이라는 이름 있는
  함수로 분리한다.
- `create_rag_chain()` 안에서 `prompt`, `model`, `parser` 변수를 각각 보여 준 뒤
  `prompt | model | parser`로 연결한다.
- 답변은 사용자에게 보여 줄 일반 텍스트이므로 `StrOutputParser`를 사용한다.
  비스트리밍 `/ask-rag`의 법령 출처는 FastAPI 응답 모델이 별도 필드로 관리한다.

## 사용자가 고민했던 부분

처음에는 현재 코드가 교재의 LCEL 체인과 다르게 보여, 체인 연결과 실행이
`rag.py`에서 이루어지는지 확인하기 어려웠다. inline lambda를 이름 있는 함수와
Runnable로 바꾼 뒤 `prompt | model | parser` 흐름이 직접 보이도록 정리했다.

`with_structured_output()`과 Pydantic 모델도 검토했다. 하지만 현재 생성 결과는
스트리밍 가능한 답변 문자열이고 출처는 API에서 따로 구성한다. 이 단계에서 구조화
출력을 추가하면 Judge나 Agent에 필요한 상태가 아직 없는데도 출력 계약만 복잡해진다.
도구 호출 결과나 분기 판단을 모델 출력으로 받아야 할 때 다시 검토한다.

## 결과

- 기존 parser, 임베딩, Chroma와 생성 backend 테스트를 유지할 수 있다.
- LCEL의 prompt, model, parser 역할을 작은 코드로 확인할 수 있다.
- 일반 답변 경로는 LangSmith에서 LCEL 내부 prompt와 생성 단계를 trace할 수 있다.
- 이후 LangGraph에서는 기존 검색·생성 함수를 node 안에서 재사용할 수 있다.

## 감수하는 한계

- LangChain의 전용 ChatModel이나 VectorStore retriever를 완전히 활용하는 구조는 아니다.
- 일반 응답은 LCEL `invoke()`를 사용하지만 스트리밍 응답은 같은 입력 builder와 prompt를
  거쳐 `generator.stream()`을 직접 호출한다. 두 경로의 최종 전달 방식은 아직 다르다.
- `/ask-rag/stream`은 순수 텍스트만 전송하므로 비스트리밍 응답처럼 출처 필드를 함께
  전달하지 않는다.
- LangGraph 전환에서 상태와 node가 필요해지면 함수 경계를 한 번 더 점검해야 한다.

현재 단계에서는 이 한계를 추상화로 미리 해결하지 않는다. 먼저 같은 Dataset으로
LangChain 기준선을 남기고, LangGraph로 실행 구조만 옮긴 뒤 필요한 차이만 보완한다.
