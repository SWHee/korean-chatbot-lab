# Agent 배포 작업 순서

- 갱신일: 2026-08-06
- 목표: 로컬에서 검증한 `web + api` 구성을 EC2 자동 배포까지 그대로 사용

## 1. 파일이 맡는 역할

| 파일 | 쉬운 설명 |
| --- | --- |
| `Dockerfile` | FastAPI 실행에 필요한 코드와 패키지를 한 이미지로 포장 |
| `frontend/Dockerfile` | Next.js를 개발 서버가 아닌 production 이미지로 포장 |
| `.dockerignore` | 이미지에 복사하지 않을 secret·cache·SQLite 목록 |
| `docker-compose.yml` | 두 컨테이너의 주소, 포트, 환경 변수와 저장 공간 연결 |
| `.github/workflows/deploy.yml` | push 후 검사·이미지 발행·EC2 재시작 자동화 |

## 2. 자주 보이는 문법

```yaml
ports:
  - "3000:3001"
```

왼쪽 `3000`은 EC2와 브라우저에서 접속할 포트이고, 오른쪽 `3001`은 Next.js
컨테이너 내부 포트다.

```yaml
environment:
  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY in .env}
```

`${...}`는 Compose가 실행될 때 `.env`의 값을 넣는 문법이다. `:?` 뒤 문장은 값이
없을 때 보여 줄 오류다. 실제 key가 Compose 파일이나 이미지에 들어가지는 않는다.

```yaml
volumes:
  - ./data/index:/app/data/index
  - agent_runtime:/app/.runtime
```

첫 줄은 EC2의 실제 폴더를 컨테이너에 연결하는 **bind mount**다. 두 번째 줄은 Docker가
관리하는 **named volume**이라 컨테이너를 새로 만들어도 SQLite 대화 상태가 남는다.

`build`는 로컬에서 Dockerfile로 이미지를 만들 때 사용하고, `image`는 Docker Hub에서
올리거나 내려받을 이미지 이름이다. 같은 service에 둘 다 적어 로컬 build와 EC2 pull이
한 Compose 파일을 공유한다.

## 3. 로컬 최초 준비

루트 `.env`에 실제 값을 넣는다.

```dotenv
ANTHROPIC_API_KEY=실제키
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_TIMEOUT_SECONDS=60
FINLIFE_API_KEY=실제키
```

Docker Desktop을 켠 뒤 프로젝트 루트에서 실행한다.

```bash
docker compose build api web
docker compose run --rm api python scripts/build_index.py
docker compose up -d --wait
docker compose ps
```

- `build`: 두 프로젝트 이미지를 생성
- `run --rm`: 인덱싱용 임시 API 컨테이너를 실행하고 끝나면 삭제
- `up -d`: 컨테이너를 백그라운드에서 실행
- `--wait`: healthcheck가 통과할 때까지 기다림

이미 인덱스가 있다면 `build_index.py`는 다시 실행하지 않는다. 브라우저에서
`http://localhost:3000`을 열고 법령 질문 1건과 상품 조건을 이어 말하는 두 턴을
확인한다.

종료할 때는 다음 명령을 사용한다.

```bash
docker compose down
```

`down`은 컨테이너와 network만 내린다. `-v`를 붙이지 않으면 KURE cache와 SQLite
volume은 남는다.

## 4. Docker Hub 수동 확인

Docker Hub에 `korean-chatbot-api`, `korean-chatbot-web` repository를 준비한다.

```bash
docker login
DOCKERHUB_USERNAME=<사용자명> docker compose build api web
docker push <사용자명>/korean-chatbot-api:latest
docker push <사용자명>/korean-chatbot-web:latest
```

프로젝트가 직접 만드는 이미지는 두 개뿐이다.

## 5. EC2 최초 한 번 준비

EC2의 `~/korean-chatbot`에 최신 `docker-compose.yml`을 둔다. 같은 폴더의 `.env`에는
다음 값을 준비한다.

```dotenv
DOCKERHUB_USERNAME=<Docker Hub 사용자명>
ANTHROPIC_API_KEY=실제키
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_TIMEOUT_SECONDS=60
FINLIFE_API_KEY=실제키
```

그 다음 EC2 터미널에서 실행한다.

```bash
cd ~/korean-chatbot
mkdir -p data/index
docker compose pull api web
docker compose run --rm api python scripts/build_index.py
docker compose up -d --wait
curl --fail http://127.0.0.1:3000
```

보안 그룹은 SSH `22`를 내 IP로 제한하고 사용자 화면용 `3000`만 필요한 범위에 연다.
FastAPI `8000`은 외부에 공개하지 않는다.

## 6. GitHub Actions secret

GitHub repository의 Actions secrets에 다음 값만 등록한다.

- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY`

Anthropic·Finlife key는 EC2 `.env`에만 둔다. workflow가 매번 key를 복사하지 않으므로
로그 노출 위험과 설정 중복을 줄인다.

`main` push 후 workflow는 테스트와 프론트 build를 통과한 commit만 이미지로 만들고,
`latest`와 commit SHA 두 tag를 발행한다. EC2는 해당 SHA 이미지를 정확히 pull해
재시작한 뒤 healthcheck와 `3000` HTTP 응답을 확인한다.

## 7. 매일 종료와 재시작

EC2 인스턴스를 중지하기 전에는 별도 Docker 삭제가 필요 없다. 다음 작업일에 인스턴스를
시작하고 확인한다.

```bash
cd ~/korean-chatbot
docker compose up -d --wait
docker compose ps
```

EBS와 Docker volume은 인스턴스를 중지해도 남고, 저장 비용은 계속 발생한다. 실습을
완전히 끝낼 때만 snapshot 필요 여부를 확인한 뒤 인스턴스·EBS를 삭제한다.
