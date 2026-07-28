# Docker·EC2·GitHub Actions 실습 순서

- 작성일: 2026-07-27
- 목표: 서버를 직접 배포한 뒤 `main` push로 같은 배포를 자동 실행

## 먼저 알아둘 파일

| 파일 | 쉬운 설명 |
| --- | --- |
| `Dockerfile` | FastAPI 이미지를 만드는 조리법 |
| `.dockerignore` | 이미지에 넣지 않을 파일 목록 |
| `docker-compose.yml` | FastAPI와 Ollama 컨테이너를 함께 실행하는 설정 |
| `.github/workflows/deploy.yml` | GitHub가 자동으로 실행할 명령 |

## 전체 흐름

```text
Dockerfile
  → FastAPI 이미지 생성
  → Docker Hub에 push
  → EC2가 이미지를 pull
  → docker compose up

main push
  → GitHub Actions가 위 작업을 자동 실행
```

이번 실습에서 직접 만드는 이미지는 FastAPI 이미지 하나다. Ollama 이미지는
Docker Hub에 이미 만들어져 있으므로 pull해서 사용한다.

## 1. 로컬에서 Docker 이미지 실행

### 이미지 만들기

```bash
docker build -t local/korean-chatbot:latest .
```

이미지는 실행 전의 묶음이고, 컨테이너는 그 이미지를 실제로 실행한 상태다.

### FastAPI만 실행해 보기

```bash
docker run --rm -p 8000:8000 local/korean-chatbot:latest
```

`http://localhost:8000/docs`가 열리면 FastAPI 이미지의 기본 실행은 성공이다.
아직 Ollama와 연결하지 않았으므로 RAG 질문까지 확인하지는 않는다.

## 2. Docker Compose로 함께 실행

### 컨테이너 시작

```bash
docker compose up -d --build
```

이 명령은 다음 두 컨테이너를 실행한다.

- `api`: 우리가 만든 FastAPI 이미지
- `ollama`: Docker Hub에서 받은 Ollama 이미지

### Ollama 모델 받기

최초 한 번만 실행한다.

```bash
docker compose exec ollama \
  ollama pull qwen3:4b-instruct-2507-q4_K_M
```

### Chroma 인덱스 만들기

최초 한 번만 실행한다.

```bash
docker compose run --rm api uv run python scripts/build_index.py
```

### 확인과 종료

```bash
docker compose ps
curl http://localhost:8000/openapi.json
docker compose down
```

RAG까지 확인할 때는 다시 `docker compose up -d`한 뒤 `/ask-rag`에 질문 한 건을
보낸다.

## 3. Docker Hub와 EC2에서 수동 실행

### Docker Hub 준비

Docker Hub에 `korean-chatbot` public repository 하나를 만든다. 로컬 터미널에서
로그인한 뒤 FastAPI 이미지를 올린다.

```bash
docker login
docker tag local/korean-chatbot:latest \
  <DOCKERHUB_USERNAME>/korean-chatbot:latest
docker push <DOCKERHUB_USERNAME>/korean-chatbot:latest
```

다시 pull할 수 있으면 이미지 업로드가 확인된다.

```bash
docker pull <DOCKERHUB_USERNAME>/korean-chatbot:latest
```

### EC2 최초 준비

EC2 한 대를 만들고 다음 항목을 준비한다.

1. Docker와 Docker Compose 설치
2. 보안 그룹에서 SSH `22`는 내 IP만 허용
3. 실습용 FastAPI `8000` 포트 허용
4. `~/korean-chatbot`에 `docker-compose.yml` 복사
5. 같은 폴더의 `.env`에 Docker Hub 사용자명 작성

```dotenv
DOCKERHUB_USERNAME=<DOCKERHUB_USERNAME>
```

EC2에서도 로컬과 같은 순서로 실행한다.

```bash
cd ~/korean-chatbot
docker compose pull
docker compose up -d
docker compose exec ollama \
  ollama pull qwen3:4b-instruct-2507-q4_K_M
docker compose run --rm api uv run python scripts/build_index.py
```

브라우저에서 `http://<EC2_PUBLIC_IP>:8000/docs`가 열리고 RAG 질문도 성공하면
수동 배포가 끝난다.

## 4. GitHub Actions로 자동화

GitHub repository의 `Settings > Secrets and variables > Actions`에 다음 값을 넣는다.

| Secret | 내용 |
| --- | --- |
| `DOCKERHUB_USERNAME` | Docker Hub 사용자명 |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `EC2_HOST` | EC2 public IP 또는 주소 |
| `EC2_USERNAME` | EC2 SSH 사용자명 |
| `EC2_SSH_KEY` | EC2 SSH private key 전체 내용 |

`main`에 push하면 `deploy.yml`이 다음 순서로 실행된다.

1. pytest 실행
2. FastAPI 이미지 build
3. Docker Hub에 `latest` 이미지 push
4. SSH로 EC2 접속
5. EC2에서 `docker compose pull api`
6. EC2에서 `docker compose up -d`

Ollama 모델과 Chroma 인덱스는 EC2의 volume과 폴더에 남기 때문에 이미지가 바뀔
때마다 다시 만들지 않는다.

## 완료 기준

- 로컬에서 `docker compose up` 성공
- Docker Hub에서 FastAPI 이미지 확인
- EC2 외부에서 Swagger와 RAG 요청 성공
- `main` push 뒤 GitHub Actions 성공
- EC2의 API 컨테이너가 새 이미지로 다시 실행됨

이번 기본 실습에서는 ECR, AWS OIDC, SSM, HTTPS, 자동 롤백은 다루지 않는다.
필요성이 생기면 챌린지 완료 뒤 하나씩 추가한다.

## 참고

- [uv Docker 사용법](https://docs.astral.sh/uv/guides/integration/docker/)
- [Docker Compose 문서](https://docs.docker.com/reference/compose-file/)
- [Docker GitHub Actions](https://docs.docker.com/build/ci/github-actions/)
- [Ollama Docker 이미지](https://hub.docker.com/r/ollama/ollama)
- [SSH Action](https://github.com/appleboy/ssh-action)
