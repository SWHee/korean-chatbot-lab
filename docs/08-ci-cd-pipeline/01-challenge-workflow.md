# 현재 프로젝트 전체를 배포하는 작업 순서

- 갱신일: 2026-07-30
- 목표: 현재 구현 전체를 로컬 Compose, EC2, GitHub Actions에서 같은 구조로 실행
- 방식: 최종 파일을 단계마다 보강하는 바텀업 작업

## 현재 위치

로컬 Compose에서 브라우저 질문과 스트리밍 답변까지 확인했다. 다음은 Docker Hub에
API·web 이미지를 직접 올리고 다시 내려받는 수동 검증이다.

## 현재 구성과 기존 Docker 파일의 차이

현재 사용자가 실제로 이용하는 흐름은 다음과 같다.

```text
브라우저
  → Next.js :3000
  → Next.js /api/chat proxy
  → FastAPI :8000
  → Chroma·KURE-v1
  → Ollama :11434
```

이번 정리 전 `Dockerfile`과 `docker-compose.yml`은 FastAPI와 Ollama까지만
포함했다. 현재는 Next.js 이미지와 `web` service, 두 프로젝트 이미지의
GitHub Actions build·push까지 같은 실행 계약으로 맞췄다.

## 최종 실행 계약

### 서비스

| Compose service | 이미지 | 외부 공개 |
| --- | --- | --- |
| `web` | 프로젝트의 Next.js 이미지 | `3000` |
| `api` | 프로젝트의 FastAPI 이미지 | Compose 내부 `8000` |
| `ollama` | 공식 Ollama 이미지 | Compose 내부 `11434` |

Next.js는 `CHATBOT_API_URL=http://api:8000`으로 FastAPI에 접근한다. FastAPI는
`OLLAMA_BASE_URL=http://ollama:11434`로 Ollama에 접근한다. 브라우저에는 Next.js만
공개하고 API와 Ollama는 Compose network 안에서 통신하게 한다.

### 보존 데이터

- `data/index`: 재생성 가능한 Chroma 인덱스
- Hugging Face cache: KURE-v1 모델
- Ollama volume: Qwen3 모델

이미지에는 코드와 고정 의존성만 넣고 `.env`, 모델 파일, 로컬 cache와 기존 index는
넣지 않는다.

## 1단계. 실행 계약과 파일 책임 확정

먼저 최종 파일이 맡을 역할을 고정한다.

| 파일 | 최종 역할 |
| --- | --- |
| 루트 `Dockerfile` | FastAPI runtime 이미지 |
| 루트 `.dockerignore` | 백엔드 build context 정리 |
| `frontend/Dockerfile` | Next.js production 이미지 |
| `frontend/.dockerignore` | `node_modules`, `.next` 등 제외 |
| `docker-compose.yml` | web·api·ollama와 volume·network 연결 |
| `.github/workflows/deploy.yml` | 두 이미지 검사·발행·EC2 갱신 |

이 단계부터 이름, 포트, 환경 변수와 volume 경로를 뒤 단계에서 다시 바꾸지 않을
기준으로 사용한다.

## 2단계. FastAPI 이미지 완성

현재 루트 `Dockerfile`을 최종 백엔드 이미지로 다듬는다.

1. Linux에서는 CPU 전용 PyTorch를 사용하도록 `pyproject.toml`과 `uv.lock` 갱신
2. 개발 의존성과 uv 다운로드 cache를 이미지에서 제외
3. 법령 XML과 인덱스 생성 스크립트 포함
4. `linux/amd64` 기준 build 확인
5. 이미지 안에서 pytest가 아니라 runtime import와 FastAPI 시작 확인
6. KURE-v1 임베딩과 Chroma 경로 확인

완료 기준:

- CUDA·NVIDIA package가 backend 이미지에 없음
- 기존 약 3.2GB 이미지보다 크기가 의미 있게 줄어듦
- `/openapi.json`과 RAG 요청에 필요한 Python import가 성공함
- 이후 Compose와 CI가 같은 Dockerfile을 사용함

## 3단계. Next.js 이미지 완성

현재 `frontend/`를 production mode로 실행하는 이미지를 만든다.

1. `package-lock.json` 기준 `npm ci`
2. `npm run build`
3. 개발 서버가 아닌 production server 실행
4. `public/financial-guardian.png` 등 실제 UI 자산 포함
5. 컨테이너의 `CHATBOT_API_URL`로 FastAPI service 연결

완료 기준:

- 깨끗한 build context에서 Next.js production build 성공
- 컨테이너가 `3000`에서 실행됨
- 브라우저 요청이 Next.js proxy를 거쳐 FastAPI stream을 받음

## 4단계. 최종 Docker Compose 완성

백엔드와 프론트엔드 Dockerfile을 `web`, `api`, `ollama` 세 service로 연결한다.

1. service 이름을 내부 hostname으로 사용
2. 외부에는 Next.js `3000`만 공개
3. Ollama 모델, KURE-v1 cache, Chroma index를 volume으로 보존
4. Ollama 모델 pull과 Chroma index build를 최초 1회 준비 절차로 명시
5. service별 healthcheck와 시작 순서 확인
6. `docker compose down` 후 다시 올려도 모델·index가 남는지 확인

전체 확인은 다음 한 경로로 한다.

```text
브라우저 질문
  → web
  → api
  → Chroma 검색
  → Ollama 생성
  → web 스트리밍 답변
```

Swagger만 열리는 것으로 완료하지 않는다. 현재 사용자가 실제로 보는 Next.js 화면에서
RAG 답변 한 건이 끝까지 도착해야 로컬 컨테이너 구성이 완료된다.

## 5단계. CI에서 전체 프로젝트 검사

배포 전에 GitHub Actions가 다음 순서로 현재 프로젝트 전체를 확인하게 한다.

1. Python dependency 설치와 pytest
2. Next.js `npm ci`와 production build
3. FastAPI 이미지 build
4. Next.js 이미지 build

`test` job에서 Python 전체 테스트와 Next.js production build를 먼저 확인한다.
이 job이 통과한 경우에만 `build-and-deploy` job이 두 이미지를 build·push하고
EC2 갱신을 실행한다.

## 6단계. Docker Hub에 두 이미지 발행

프로젝트용 repository를 두 개 사용한다.

- `<사용자명>/korean-chatbot-api`
- `<사용자명>/korean-chatbot-web`

GitHub Actions가 두 이미지를 `linux/amd64`로 build하고 push한다. Ollama 이미지는
프로젝트가 다시 build하지 않고 EC2가 공식 이미지를 직접 pull한다.

완료 기준:

- Docker Hub에서 두 프로젝트 이미지 확인
- 새 환경에서 두 이미지를 pull 가능
- 이미지 이름이 `docker-compose.yml`과 일치

## 7단계. EC2에 같은 Compose 수동 배포

자동화 전에 로컬에서 완성한 Compose를 EC2에 그대로 옮긴다.

1. EC2 CPU architecture와 두 이미지 platform 일치 확인
2. Docker Engine과 Compose plugin 설치
3. `docker-compose.yml`과 배포용 `.env` 준비
4. 세 이미지 pull
5. Ollama 모델과 Chroma index 최초 준비
6. `docker compose up -d`
7. 외부 `http://<EC2_PUBLIC_IP>:3000`에서 RAG 질문 확인

보안 그룹은 SSH `22`를 내 IP로 제한하고, 사용자 화면용 `3000`만 실습 범위에서
공개한다. FastAPI `8000`과 Ollama `11434`는 외부에 열지 않는다.

## 8단계. GitHub Actions 자동 배포

수동 배포에서 성공한 명령만 workflow에 옮긴다.

```text
main push
  → backend test
  → frontend build
  → api·web image build/push
  → EC2에 최신 docker-compose.yml 복사
  → EC2 SSH
  → docker compose pull
  → docker compose up -d
  → 외부 UI 확인
```

EC2에는 Ollama 모델과 Chroma index가 이미 남아 있으므로 매 배포마다 다시 만들지
않는다. Compose 파일은 코드와 서비스 구성이 어긋나지 않도록 매번 최신 파일을
복사한다. 자동 배포 완료 기준은 workflow의 성공 표시뿐 아니라 EC2의 Next.js
화면에서 질문 한 건이 새 컨테이너 경로로 처리되는 것이다.

## 이번 챌린지에서 제외하는 범위

- 아직 구현 전인 Finlife Agent
- 선택 기능인 LangFeather server
- HTTPS·도메인·Nginx
- ECR·OIDC·SSM
- 무중단 배포와 자동 rollback
- 여러 EC2 instance

이 항목들은 현재 프로젝트 전체를 한 EC2에서 재현하는 기본 파이프라인이 끝난 뒤
필요에 따라 추가한다.
