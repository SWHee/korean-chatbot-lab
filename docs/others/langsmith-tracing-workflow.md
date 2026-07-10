# LangSmith 추적 워크플로우

LangSmith는 지금 만든 RAG가 실제로 어떤 순서로 움직이는지 눈으로 확인하기 위해
붙인다. 아직은 점수를 많이 만들기보다, 한 요청 안에서 검색과 생성이 어떻게
이어지는지 보는 것이 먼저다.

## 왜 지금 붙이나

현재 프로젝트에는 이미 법령 인덱스, retriever, LCEL RAG 체인이 있다. 그래서
LangSmith를 붙이면 처음부터 빈 화면을 보는 것이 아니라, 실제 `/ask-rag` 요청이
어떤 흐름으로 처리되는지 바로 확인할 수 있다.

지금 보고 싶은 것은 세 가지다.

- 질문이 어떤 prompt로 바뀌는지
- 어떤 법령 조문이 검색되어 context에 들어가는지
- 답변이 검색 근거 안에서 만들어졌는지

## 1차 목표: LCEL 체인 trace 확인

먼저 `rag.py`의 LCEL 체인이 LangSmith에 보이는지 확인한다. 공식 문서 기준으로
LangChain 코드는 환경 변수를 설정하면 trace가 남는다.

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<발급받은 키>
LANGSMITH_PROJECT=korean-chatbot-rag-dev
```

로컬에서는 `.env.example`을 복사해 `.env`를 만들고, `LANGSMITH_API_KEY` 값만
실제 키로 바꾼다. 서버는 시작할 때 `.env`를 자동으로 읽는다.

```bash
cp .env.example .env
# .env 안의 LANGSMITH_API_KEY 값을 실제 키로 수정
uv run fastapi dev
```

이 상태에서 서버를 실행하고 `/ask-rag`를 호출하면 LangSmith project에서 trace를
확인한다. 처음에는 `/ask-rag/stream`보다 `/ask-rag`가 보기 쉽다. JSON 응답에
답변과 sources가 같이 있기 때문이다.

확인할 화면은 다음 정도면 충분하다.

- 입력 질문
- prompt에 들어간 법령 context
- 생성 모델에 전달된 최종 메시지
- 모델이 만든 답변
- 각 단계에 걸린 시간

## 2차 목표: retriever 단계도 따로 보기

LCEL trace만으로는 검색 단계가 충분히 잘 보이지 않을 수 있다. 우리 retriever는 직접
만든 Python 함수이고, Chroma 검색도 LangChain retriever 객체가 아니기 때문이다.

하지만 처음부터 수동 trace를 많이 붙이면 화면이 복잡해진다. 그래서 1차에서는
환경 변수와 LCEL trace만 확인한다. 검색 단계가 충분히 보이지 않는다는 것을 직접
확인한 뒤, 그때 `retrieve_articles` 주변에 얇은 수동 trace를 추가한다.

```text
ask-rag 요청
  → retrieve_articles
  → format_context
  → generate answer
```

이렇게 나눠 보면 "답변이 이상한 이유"를 더 쉽게 찾을 수 있다. 예를 들어 보호
한도 질문에서 정답 조문이 검색되지 않았다면, 생성 모델 문제가 아니라 retriever
문제로 볼 수 있다.

## 무엇을 보고 개선하나

| LangSmith에서 보는 것 | 알 수 있는 것 | 다음 개선 후보 |
| --- | --- | --- |
| 검색된 sources | 질문에 맞는 조문이 들어왔는지 | 청킹, top-k, 질의 변환 |
| 최종 prompt | 근거가 너무 길거나 부족한지 | context 포맷, prompt 문구 |
| 모델 답변 | 근거 밖 내용을 말하는지 | system prompt 강화 |
| 단계별 시간 | 어디서 오래 걸리는지 | 모델 로드, 질문 임베딩, 생성 지연 확인 |

지금 단계에서는 "정답률 몇 점"보다 "왜 이런 답이 나왔는지 설명할 수 있는가"가 더
중요하다. 평가 지표는 trace를 몇 번 보면서 실패 유형이 보인 뒤에 붙이는 편이
자연스럽다.

## 우리 프로젝트의 진행 순서

1. `.env`에 LangSmith 키와 project 이름을 넣는다.
2. `/ask-rag` 한 번을 실행해 LCEL trace가 남는지 확인한다.
3. trace에서 prompt, context, 답변을 직접 확인한다.
4. 검색 단계가 잘 안 보이면 `retrieve_articles` 주변에 수동 trace를 추가한다.
5. 같은 질문을 여러 번 실행해 "검색 실패"와 "생성 실패"를 구분한다.
6. 그 다음에 작은 평가셋으로 offline evaluation을 붙인다.

LangGraph는 이 다음 문제다. 먼저 현재 RAG 흐름을 LangSmith에서 설명할 수 있어야,
나중에 graph node가 늘어나도 어느 단계가 문제인지 따라갈 수 있다.

공식 문서:

- https://docs.langchain.com/langsmith/observability
- https://docs.langchain.com/langsmith/trace-with-langchain
- https://docs.langchain.com/langsmith/observability-quickstart
