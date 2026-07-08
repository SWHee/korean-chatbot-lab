# Korean Chatbot Learning Project

한국어 챗봇을 만들며 로컬 생성 모델 서빙부터 법령 RAG와 평가까지 단계적으로
학습하는 프로젝트다. 기능 수보다 각 단계의 입력·출력과 선택 이유를 직접
설명할 수 있는 상태를 목표로 한다.

## 현재 상태

생성 모델 서빙과 법령 RAG의 기본 질의 흐름까지 구현했다.

- `Qwen/Qwen3-4B-Instruct-2507` Hugging Face 생성기
- `qwen3:4b-instruct-2507-q4_K_M` Ollama 생성기(기본 backend)
- FastAPI `POST /chat`, `POST /chat/stream`
- FastAPI `POST /ask-rag`
- 소비자보호 법령 XML 4건 수집 및 조문 단위 파싱
- 조문 경계 보존 청킹: 260개 조문 → 삭제 스텁 2건 제외 → 322개 청크
- KURE-v1 임베딩과 Chroma 인덱스
- 평가 질문 기반 임베딩·검색 검증
- LangChain LCEL 기반 최소 RAG 체인

## 현재 구조

일반 생성과 RAG 답변은 endpoint를 분리한다.

```text
POST /chat, /chat/stream
          |
      Generator interface
       /               \
OllamaGenerator       HF Generator

law XML → Article → Chunk → KURE-v1 → Chroma
                                          |
POST /ask-rag → retrieve_articles(top-k) → LCEL RAG chain
```

생성 쪽은 프로젝트가 소유하는 `generate()`·`stream()` 경계에 의존한다.
Ollama와 Transformers 구현을 분리해 모델 실행 방식이 FastAPI endpoint로
퍼지지 않게 했다.

RAG 쪽은 법령 수집, 파싱, 청킹, 임베딩, 벡터 검색을 작은 모듈로 분리했다.
LangChain을 연결할 때도 이 구현을 교체하지 않고 흐름을 조합하는 데만 사용한다.

## 개발 환경

- Python 3.13
- uv
- pytest
- Ollama

```bash
uv venv --python 3.13 --prompt ko-chat
uv sync --locked
source .venv/bin/activate
```

## 챗봇 실행

기본 backend는 Ollama다. 먼저 Ollama에서 모델을 준비한 뒤 API 서버를 실행한다.

```bash
ollama pull qwen3:4b-instruct-2507-q4_K_M
uv run uvicorn chatbot.main:app --host 127.0.0.1 --port 8000
```

Hugging Face backend를 사용하려면 환경 변수를 지정한다.

```bash
CHATBOT_BACKEND=hf uv run uvicorn chatbot.main:app --host 127.0.0.1 --port 8000
```

일괄 응답 요청:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"예금자보호제도가 무엇인가요?"}'
```

스트리밍 응답 요청:

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt":"예금자보호제도가 무엇인가요?"}'
```

두 endpoint 모두 `{"prompt": "질문"}` 형식의 JSON body를 사용한다.
Swagger UI에서는 스트리밍 응답도 화면에 모아서 표시할 수 있으므로 실제 조각
전송 확인에는 `curl -N`이 더 적합하다.

법령 RAG 답변 요청:

```bash
curl -X POST http://127.0.0.1:8000/ask-rag \
  -H "Content-Type: application/json" \
  -d '{"question":"은행이 파산하면 내 예금은 얼마까지 보호받나요?"}'
```

`/ask-rag`는 `{"question": "질문"}` 형식의 JSON body를 사용한다. 응답에는
생성 답변, 검색에 사용한 법령 출처, 처리 시간이 포함된다. 최초 호출 시
KURE-v1 임베딩 모델과 Chroma 인덱스를 준비하므로 `/chat`보다 시작 비용이 크다.

## 법령 인덱스

원문 XML은 `data/laws/`에 포함되어 있다. 파생물인 Chroma 인덱스는 Git에
포함하지 않고 필요할 때 재생성한다.

```bash
uv run python scripts/build_index.py
uv run python scripts/verify_index.py
```

수집부터 다시 실행하는 방법과 snapshot 정보는
[`data/laws/README.md`](data/laws/README.md)에 있다.
원문 XML과 조문·청크처럼 사람이 확인 가능한 파생 데이터는 출처와 snapshot을
명시하면 저장소에 남길 수 있다. Chroma 인덱스, 모델 weight, cache처럼 재생성
가능한 바이너리성 파생물은 커밋하지 않는다.

## 평가

평가 질문은 [`docs/evaluation/rag-questions.md`](docs/evaluation/rag-questions.md)에
24개가 있다. 현재 15개 질문에는 retrieval 정답 조문이 연결되어 있으며,
임베딩 모델 비교와 Chroma 검색 검증에 사용한다.

```bash
uv run python scripts/compare_embeddings.py
uv run pytest
```

최종 답변의 정확성·근거성·범위 밖 질문 처리는 `/ask-rag` 기준으로 LangSmith
실험에서 평가한다.

## 주요 디렉터리

```text
korean-chatbot/
├── data/laws/                 # 법령 XML 원문
├── docs/
│   ├── adr/                   # 설계 결정
│   ├── devlog/                # 구현 과정에서 얻은 핵심 학습
│   ├── evaluation/            # 평가 질문
│   └── others/                # 실행·확인 가이드
├── scripts/                   # 수집·비교·인덱싱·검증
├── src/chatbot/
│   ├── generator.py           # Hugging Face 생성
│   ├── ollama_generator.py    # Ollama 생성
│   ├── main.py                # FastAPI
│   ├── statutes.py            # XML 조문 파싱
│   ├── chunking.py            # 조문 청킹
│   ├── embedding.py           # KURE-v1 임베딩
│   ├── retriever.py           # 질문 임베딩과 조문 검색
│   ├── rag.py                 # LCEL RAG 체인
│   └── vectorstore.py         # Chroma 검색
└── tests/
```

초기에 직접 구현한 작은 Transformer는
[`experiments/from_scratch/`](experiments/from_scratch/)에 보존하며 주력 코드와
섞지 않는다.
