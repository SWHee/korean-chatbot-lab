# Korean Chatbot Lab

로컬 LLM으로 한국어 금융 안내 챗봇을 만들며, 생성 모델 서빙부터 법령 RAG까지
단계적으로 익히는 프로젝트입니다. 현재는 예·적금 이용자가 궁금해할
소비자보호 제도를 법령 근거와 함께 설명하는 흐름에 집중하고 있습니다.

> 이 프로젝트의 답변은 학습·시연용입니다. 최신 법령, 개별 상품의 보호 여부,
> 금융 의사결정은 반드시 공식 공시와 관계 기관 정보를 다시 확인해야 합니다.

## 한눈에 보기

| 구분 | 현재 구현 |
| --- | --- |
| 생성 모델 | Qwen3-4B-Instruct-2507 · 기본 실행은 Ollama q4_K_M |
| API | 법령 RAG의 JSON·스트리밍 요청 제공 |
| RAG 데이터 | 금융소비자보호법·예금자보호법과 각 시행령, 총 4건 |
| 검색 | KURE-v1 임베딩(1024차원) · Chroma 벡터스토어 |
| 평가 | LangSmith Dataset 24문항 · 검색 Precision/Recall · Gemini Faithfulness |
| 검증 | pytest와 임베딩·인덱스 재현 스크립트 |

## 아키텍처

```mermaid
flowchart LR
    U[사용자 질문] --> UI[Streamlit 채팅 UI]
    UI --> API[FastAPI]

    G[Generator 경계]
    G --> O[Ollama Qwen3<br/>기본 backend]
    G -. 선택 .-> H[Hugging Face Qwen3]

    API --> R[/ask-rag · /ask-rag/stream/]
    R --> E[KURE-v1<br/>질문 임베딩]
    E --> V[(Chroma<br/>법령 인덱스)]
    V --> T[Retriever<br/>상위 조문 선택]
    T --> L[LCEL RAG 체인]
    L --> G

    X[국가법령정보 Open API<br/>법령 XML 4건] --> P[파싱 · 청킹 · 임베딩]
    P --> V
```

법령 RAG는 질문과 가까운 조문을 먼저 찾아 모델에 함께 제공하므로, 답변과 함께
검색에 사용한 법령 출처를 확인할 수 있습니다.

## 현재 완료한 범위

- Qwen3 기반 로컬 생성기와 Ollama backend 전환
- FastAPI 법령 RAG JSON·순수 텍스트 스트리밍 API
- 법령 XML 수집, 조문 파싱, 조문 경계 기반 청킹
- KURE-v1 모델 비교·선정과 Chroma 인덱스 생성
- 질문 임베딩 → 조문 검색 → LCEL 답변 생성의 최소 RAG 흐름
- Streamlit 기반 법령 RAG 채팅·스트리밍 화면
- LangSmith 24문항 Dataset과 LangChain v1 기준선 평가

## 다음에 이어갈 범위

- 현재 RAG 동작을 유지한 최소 StateGraph 전환
- 같은 Dataset으로 LangChain과 LangGraph 결과 비교
- 금융상품 한눈에 API로 최신 예·적금 상품 후보 조회 연결

첫 LangGraph 단계에서는 검색과 답변 생성을 graph node로 옮기기만 합니다. 기준선과
같은 결과가 나오는지 확인한 뒤 상품 API 분기와 상태 관리를 추가할 예정입니다.

## 빠르게 실행하기

### 1. 환경 준비

Python 3.13과 [uv](https://docs.astral.sh/uv/)를 사용합니다.

```bash
uv sync --locked
```

기본 backend는 Ollama입니다. Ollama를 설치한 뒤 모델을 준비합니다.

```bash
ollama pull qwen3:4b-instruct-2507-q4_K_M
```

### 2. 법령 인덱스 만들기

저장소에는 법령 XML 원문만 포함합니다. 검색용 Chroma 인덱스는 아래 명령으로
로컬에서 생성합니다.

```bash
uv run python scripts/build_index.py
```

### 3. 서버 실행

```bash
uv run fastapi dev
```

서버와 Swagger UI는 각각 다음 주소에서 확인할 수 있습니다.

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

Hugging Face backend를 확인하고 싶다면 서버 실행 전에 환경 변수를 지정합니다.

```bash
CHATBOT_BACKEND=hf uv run fastapi dev
```

### 4. 채팅 UI 실행

FastAPI 서버를 켜 둔 상태에서 새 터미널을 열어 실행합니다.

```bash
uv run streamlit run streamlit_app.py
```

브라우저에서 `http://localhost:8501`을 열면 법령 RAG 답변을 채팅 형태로 확인할
수 있습니다. 화면에는 이전 메시지가 남지만, 현재 모델은 질문 사이의 문맥을 기억하지
않습니다.

## API 사용 예시

| Endpoint | 역할 | 응답 방식 |
| --- | --- | --- |
| `POST /ask-rag` | 법령 검색 후 답변과 출처 반환 | JSON |
| `POST /ask-rag/stream` | 법령 검색 후 답변을 텍스트 조각으로 전송 | plain text stream |

법령 RAG 요청:

```bash
curl -X POST http://127.0.0.1:8000/ask-rag \
  -H "Content-Type: application/json" \
  -d '{"question":"은행이 파산하면 내 예금은 얼마까지 보호받나요?"}'
```

스트리밍은 터미널에서 `-N` 옵션으로 조각 전송을 바로 확인할 수 있습니다.

```bash
curl -N -X POST http://127.0.0.1:8000/ask-rag/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"예금자보호제도는 무엇인가요?"}'
```

`/ask-rag`는 답변, 검색 출처, 처리 시간을 JSON으로 함께 반환하므로 검증의 기준
endpoint로 사용합니다. `/ask-rag/stream`은 사용자가 답변을 기다리는 동안 자연스럽게
읽을 수 있도록 답변 본문만 전송합니다.

## 법령 RAG 데이터 흐름

```text
data/laws/*.xml
       │  국가법령정보 Open API에서 수집한 원문 snapshot
       ▼
statutes.py      XML을 조문(Article) 단위로 파싱
       ▼
chunking.py      조문 경계를 보존하며 긴 조문만 분할
       ▼
embedding.py     KURE-v1으로 정규화된 1024차원 벡터 생성
       ▼
build_index.py   문서·메타데이터·벡터를 Chroma에 저장
       ▼
retriever.py     질문과 가까운 청크를 찾고 조문 단위로 중복 제거
       ▼
rag.py           조문 근거를 prompt에 넣어 답변 생성
```

현재 인덱싱 결과는 **260개 조문에서 322개 청크**입니다. 조문이 매우 긴 경우에만
내부를 나누고, 각 청크에는 법령명·조문번호·시행일을 함께 보관합니다. 따라서
검색 결과를 답변의 근거로 다시 표시할 수 있습니다.

원문 출처, 수집 snapshot, 재수집 방법은 [data/laws/README.md](data/laws/README.md)에서
확인할 수 있습니다. Chroma 인덱스와 모델 cache는 재생성 가능한 로컬 산출물이므로
Git에 올리지 않습니다.

## 검증과 참고 문서

```bash
uv run pytest
uv run python scripts/verify_index.py
```

| 문서 | 내용 |
| --- | --- |
| [RAG 파이프라인 개요](docs/02-langchain-rag/03-guides/01-rag-pipeline-overview.md) | 코드 파일별 인덱싱·검색 흐름 |
| [외부 데이터와 API](docs/06-other/01-external-data-sources.md) | 법령 원문·금융상품 한눈에 API의 역할과 저장 기준 |
| [RAG 평가 질문](docs/03-langsmith-evaluation/02-rag-questions.md) | retrieval 평가용 질문과 정답 조문 기준 |
| [RAG 기준선 평가 순서](docs/03-langsmith-evaluation/03-rag-baseline-workflow.md) | LangGraph 전후를 같은 Dataset으로 비교하는 순서 |
| [LangChain v1 기준선 결과](docs/03-langsmith-evaluation/06-langchain-baseline-results.md) | 24문항 검색·답변 평가 결과 |
| [첫 기준선 문제 해결](docs/03-langsmith-evaluation/08-langchain-baseline-troubleshooting.md) | 첫 평가에서 겪은 오류와 확인 순서 |
| [LangGraph 전환 계획](docs/04-langgraph-migration/01-langgraph-migration-plan.md) | 현재 RAG를 StateGraph로 옮기는 작은 작업 순서 |

## 디렉터리 구조

```text
korean-chatbot/
├── .streamlit/config.toml       Streamlit 색상·화면 설정
├── streamlit_app.py             법령 RAG 채팅·스트리밍 UI
├── data/
│   ├── laws/                    법령 XML 원문과 출처 정보
│   ├── evaluation/              RAG 개발·회귀 평가 Dataset
│   └── index/                   로컬 Chroma 인덱스 (Git 제외)
├── docs/
│   ├── 01-chatbot-fastapi/      모델 생성과 FastAPI 단계
│   ├── 02-langchain-rag/        RAG 설계·실험·파이프라인
│   ├── 03-langsmith-evaluation/ Dataset·추적·기준선 평가
│   ├── 04-langgraph-migration/  StateGraph 전환 계획
│   └── 06-other/                외부 데이터와 UI 기록
├── scripts/
│   ├── collect_laws.py          법령 XML 수집
│   ├── build_index.py           전체 법령 인덱스 재생성
│   ├── compare_embeddings.py    임베딩 후보 비교
│   ├── verify_index.py          Chroma 검색 결과 검증
│   ├── register_evaluation_dataset.py  LangSmith Dataset 등록
│   └── run_rag_evaluation.py    LangSmith 기준선 평가 실행
├── src/chatbot/
│   ├── main.py                  FastAPI endpoint와 앱 수명주기
│   ├── generator.py             Hugging Face Qwen3 생성기
│   ├── ollama_generator.py      Ollama Qwen3 생성기
│   ├── statutes.py              XML 조문 파싱
│   ├── chunking.py              조문 경계 기반 청킹
│   ├── embedding.py             KURE-v1 임베딩
│   ├── vectorstore.py           Chroma 컬렉션 접근과 검색
│   ├── retriever.py             질문 검색과 조문 중복 제거
│   ├── rag.py                   LCEL RAG 답변 체인
│   ├── evaluation.py            평가용 RAG 실행 결과 구성
│   ├── evaluators.py            검색·Faithfulness 평가
│   └── settings.py              로컬 환경 변수 로드
├── tests/                       단위·흐름 검증
└── experiments/from_scratch/    별도 보관한 Transformer 학습 실험
```

초기에 직접 구현한 Transformer 실험은 [experiments/from_scratch/](experiments/from_scratch/)에
별도로 보관합니다. 주력 FastAPI·RAG 코드와 섞지 않습니다.
