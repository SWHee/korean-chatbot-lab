# Korean Chatbot Learning Project

한국어 챗봇을 만들면서 사전학습 모델 활용부터 RAG와 상태 기반 agent 흐름까지
단계적으로 학습하는 프로젝트다. 높은 완성도를 한 번에 만드는 것보다, 각 단계의
입력과 출력 및 설계 이유를 직접 설명할 수 있는 상태를 목표로 한다.

## 현재 방향

초기에는 작은 PyTorch Transformer를 직접 만들며 토큰화, 데이터셋, forward,
loss를 학습했다. 이 코드는
[`experiments/from_scratch/`](experiments/from_scratch/)에 별도 실험으로
보존한다.

현재 주력 트랙은 로컬 Hugging Face instruction-tuned 모델로 생성 흐름을 먼저
구성하는 것이다. 첫 모델은 `Qwen/Qwen3-4B-Instruct-2507`로 결정했으며, M2 Pro의
MPS에서 모델을 적재하고 한국어 답변을 생성했다. FastAPI `/chat`
endpoint로 같은 생성 기능을 호출하는 흐름도 확인했다.

## 현재 설계

주력 코드를 구현할 때 프로젝트가 소유하는 작은 `Generator` 경계를 중심에 둘
계획이다.

```text
FastAPI / LangChain RAG / LangGraph
                 |
             Generator
                 |
       Hugging Face model (first)
```

처음부터 여러 모델 구현체나 복잡한 factory를 만들지는 않는다. Hugging Face
구현으로 시작하고, 외부 API 또는 from-scratch 모델을 실제로 비교할 때 같은
경계에 새로운 adapter를 추가한다.

이 선택의 상세 근거는
[`docs/adr/0001-adopt-pretrained-first.md`](docs/adr/0001-adopt-pretrained-first.md)에
기록한다. 첫 모델을 선택한 근거는
[`docs/adr/0002-select-qwen3.md`](docs/adr/0002-select-qwen3.md), 실제 고민 과정은
[`docs/devlog/chatbot/model-selection.md`](docs/devlog/chatbot/model-selection.md)에
남긴다.

## 예정된 진행 순서

1. 챗봇 용도와 평가 질문을 정의한다.
2. 사용할 Hugging Face 모델을 비교하고 선택한다.
3. 토크나이저와 모델을 불러와 한 번의 텍스트 생성을 확인한다.
4. 생성 기능을 FastAPI로 제공한다.
5. LangChain Runnable 흐름으로 연결한다.
6. 주제와 데이터를 정한 뒤 작은 RAG를 구성한다.
7. LangSmith로 검색과 답변 품질을 관찰하고 평가한다.
8. 조건 분기, 재시도 또는 상태가 필요할 때 LangGraph를 적용한다.
9. 말투나 지시 수행 개선이 필요하다는 근거가 생기면 파인튜닝을 검토한다.

각 단계에서는 함수, 클래스, endpoint 또는 기능 하나씩 구현하고 바로 검증한다.
미래 단계의 파일이나 디렉터리는 미리 만들지 않는다.

## 개발 환경

- Python 3.13
- uv
- pytest

프로젝트 루트에서 환경을 준비한다.

```bash
uv venv --python 3.13 --prompt ko-chat
uv sync --locked
source .venv/bin/activate
```

환경을 활성화하지 않고도 다음처럼 명령을 실행할 수 있다.

```bash
uv run python --version
uv run pytest --version
```

로컬 API 서버를 실행한다.

```bash
uv run uvicorn chatbot.main:app --host 127.0.0.1 --port 8000
```

`POST /chat`에 사용자 질문을 전달한다.

```json
{
  "prompt": "AI 서비스 개발자가 되기 위한 첫 단계는 무엇인가요?"
}
```

실행 환경인 `.venv`는 로컬에만 두고, `pyproject.toml`과 `uv.lock`으로 의존성을
공유한다.

## 현재 구조

```text
korean-chatbot/
├── experiments/
│   └── from_scratch/
├── docs/
│   ├── adr/
│   └── devlog/
├── src/
│   └── chatbot/
│       ├── __init__.py
│       ├── generator.py
│       └── main.py
├── .python-version
├── pyproject.toml
└── uv.lock
```

`generator.py`는 모델 적재와 답변 생성을 담당한다. `main.py`는 FastAPI
서버의 lifespan과 `/chat` endpoint, 로컬 실행 진입점을 담당한다.
