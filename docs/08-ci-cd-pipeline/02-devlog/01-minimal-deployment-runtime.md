# UI·RAG 시연용 배포 경계 정리

- 작업일: 2026-07-30
- 목표: 챗봇 화면에서 질문하고 RAG 답변을 받는 데 필요한 구성만 배포

## 판단

배포 중 계속 실행할 service는 세 개면 충분하다.

- `web`: Next.js 화면과 FastAPI proxy
- `api`: FastAPI, KURE 임베딩, Chroma 검색, LangGraph 체인
- `ollama`: Qwen3 답변 생성

Chroma와 KURE는 API 안에서 실행하므로 별도 이미지로 만들지 않았다. 평가 스크립트,
Gemini Judge, LangFeather server도 사용자 질문 경로가 아니어서 Compose에 넣지
않았다.

## 바꾼 파일과 이유

- `pyproject.toml`, `uv.lock`
  - Gemini·LangSmith 평가 직접 의존성을 `evaluation` 그룹으로 이동
  - Linux의 PyTorch를 CPU 전용 wheel로 고정해 불필요한 CUDA 패키지 제거
- 루트 `Dockerfile`
  - uv cache를 이미지 layer에 남기지 않고 배포용 non-editable 설치 사용
- `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/next.config.ts`
  - Next.js standalone production 이미지 추가
- `docker-compose.yml`
  - `web → api → ollama` 연결, 외부에는 `3000`만 공개
  - KURE cache, Chroma index, Ollama 모델은 컨테이너 밖에 보존
- `.github/workflows/deploy.yml`
  - Python 테스트와 Next.js build 뒤 API·web 이미지를 `linux/amd64`로 발행
  - 최신 Compose 파일을 EC2에 복사한 뒤 두 프로젝트 이미지와 Ollama 갱신
- 평가 실행 문서
  - 평가할 때만 `uv run --group evaluation ...`을 사용하도록 명령 수정

## 실행하고 확인한 것

```bash
uv lock
.venv/bin/pytest
cd frontend && npm run build
docker compose config --quiet
docker compose config --images
docker compose config --services
```

- Python 테스트: 77개 통과, 외부 키가 필요한 2개 제외
- Next.js production build: 성공
- standalone server 첫 화면: HTTP 200
- Compose 해석 결과: `web`, `api`, `ollama`와 이미지 3개 확인
- lockfile: Linux CUDA·NVIDIA 관련 패키지 제거 확인
- Docker 이미지 build: API와 web 모두 성공
- 로컬 이미지 크기
  - API: content 약 394MB, Docker Desktop disk usage 약 1.92GB
  - web: content 약 65MB, Docker Desktop disk usage 약 267MB
- API 이미지 확인: LangFeather 없이 `chatbot.main` import 성공

`langsmith`는 `langchain-core`의 하위 의존성이기도 해서 운영 환경에 남는다.
평가 그룹 분리로 실제 제외되는 핵심은 Gemini 연동 패키지와 `google-genai`다.

## 첫 Docker build에서 막힌 부분

첫 `docker compose build api web`은 API의 `uv sync` 단계에서 실패했다.
`python:3.13-slim`에는 Git이 없는데 운영 의존성에 GitHub 기반 LangFeather SDK가
포함돼 있어 Git 실행 파일을 찾으려 했기 때문이다.

운영 이미지에 Git을 추가하지 않고 LangFeather를 `tracing` 의존성 그룹으로 옮겼다.
`LANGFEATHER_ENABLED=true`일 때만 SDK를 불러오도록 API 코드도 바꿨다. 로컬 추적은
`uv sync --group tracing`으로 준비하며, 기본 Docker build에서는 LangFeather를
다운로드하지 않는다. 같은 build 명령을 다시 실행해 두 이미지가 만들어지는 것을
확인했다.

## 로컬 Compose 확인

모델과 인덱스를 준비한 뒤 `http://localhost:3000`에서 질문 한 건을 보내 다음
전체 경로가 동작하는 것을 확인했다.

```bash
docker image ls
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:4b-instruct-2507-q4_K_M
docker compose run --rm api python scripts/build_index.py
docker compose up -d
```

```text
브라우저 → Next.js → FastAPI → Chroma 검색 → Ollama 생성 → 스트리밍 응답
```

### Mac에서 직접 실행할 때보다 느렸던 이유

Mac에 직접 설치한 Ollama는 Apple GPU를 사용한다. 하지만 Mac의 Docker Desktop은
GPU를 컨테이너에 넘겨주지 못하므로, Docker 안의 Ollama는 CPU로 모델을 실행한다.

따라서 **같은 Qwen3 모델이어도 Docker에서는 답변 글자가 훨씬 천천히 나타날 수
있다.** Next.js 화면이 느린 것이 아니라, 답변을 만드는 Ollama의 실행 장치가
GPU에서 CPU로 바뀐 영향이 크다.

일반 CPU EC2에서도 같은 문제가 이어질 수 있다. 현재 구조를 유지하려면 느린 생성을
감수하거나 GPU instance를 사용해야 하며, 다른 선택지는 생성 단계만 외부 모델 API로
바꾸는 것이다.

- [Ollama FAQ: macOS Docker Desktop의 GPU 가속 제한](https://docs.ollama.com/faq)
- [생성 모델을 API로 바꿀 때의 영향](../03-model-backend-options.md)

## 다음 작업

로컬 Compose 검증은 완료됐다. 다음은 API·web 이미지를 Docker Hub에 직접 올리고
다시 내려받을 수 있는지 확인하는 수동 배포 단계다.
