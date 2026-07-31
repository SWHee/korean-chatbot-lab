# LangFeather 개인 실행 안내

## 1. 사전 준비

처음 한 번 다음 항목이 필요하다.

- Docker Desktop 실행
- LangFeather 저장소 clone
- Korean Chatbot 저장소의 `uv sync --group tracing` 완료

계정이나 API key는 필요하지 않다. Docker image를 처음 만들 때만 image와
dependency를 내려받기 위한 인터넷 연결이 필요하다. Korean Chatbot의 LangFeather
SDK는 `uv.lock`에 고정되어 있으므로 새 사용자는 별도의 `uv add`를 실행하지 않고
다음 명령만 실행한다.

```bash
cd /path/to/korean-chatbot
uv sync --group tracing
```

## 2. 로컬 대시보드 시작

LangFeather 저장소 터미널에서 실행한다.

```bash
cd /path/to/langfeather
docker compose up -d --build
```

정상 여부를 확인한다.

```bash
curl http://127.0.0.1:4319/api/v1/health
```

브라우저에서 `http://127.0.0.1:4319`를 연다. 이 주소의 화면과 수집 API는 같은
Docker 컨테이너가 제공하고, 기록은 `langfeather-data` Docker volume에 저장된다.
컨테이너를 재시작해도 volume을 지우지 않으면 기록이 남는다.

## 3. 추적을 켠 챗봇 서버 실행

Korean Chatbot 저장소의 새 터미널에서 다음처럼 실행한다.

```bash
cd /path/to/korean-chatbot

LANGSMITH_TRACING=false \
LANGCHAIN_TRACING_V2=false \
LANGFEATHER_ENABLED=true \
LANGFEATHER_ENDPOINT=http://127.0.0.1:4319 \
uv run --group tracing fastapi dev
```

두 LangSmith 변수를 함께 끄는 이유는 이번 확인에서 로컬 LangFeather 기록과
LangSmith 기록을 섞지 않기 위해서다. `.env`보다 위 명령의 값이 우선한다.

매번 입력하기 싫다면 개인 `.env`에 아래 두 줄을 추가해도 된다. `.env`는
Git에 올리지 않는다.

```dotenv
LANGFEATHER_ENABLED=true
LANGFEATHER_ENDPOINT=http://127.0.0.1:4319
```

## 4. 질문을 보내고 기록 확인

일반 응답은 다음 명령으로 확인한다.

```bash
curl -X POST http://127.0.0.1:8000/ask-rag \
  -H "Content-Type: application/json" \
  -d '{"question":"은행이 파산하면 예금은 얼마까지 보호되나요?"}'
```

채팅 UI를 사용하려면 FastAPI를 켜 둔 채 다른 터미널에서 실행한다.

```bash
cd frontend
npm run dev
```

질문이 끝난 뒤 LangFeather 화면을 새로고침하고
`korean-chatbot-rag` trace를 선택한다. 현재 그래프에서는 최상위 LangGraph 아래
`retrieve`, `generate` 실행과 각 단계의 입출력을 확인할 수 있어야 한다.

추적 전송은 응답 경로를 막지 않는 백그라운드 작업이다. 화면에 즉시 나타나지 않으면
잠깐 뒤 새로고침한다. 서버를 정상 종료하면 남아 있던 기록을 최대 2초 동안 전송한
뒤 닫는다.

## 5. 평소 실행과 종료

추적을 끄려면 환경 변수를 제거하거나 다음 값으로 실행한다.

```dotenv
LANGFEATHER_ENABLED=false
```

LangFeather 저장소에서 데이터는 보존하고 컨테이너만 멈춘다.

```bash
docker compose stop
```

`docker compose down -v`는 컨테이너와 함께 로컬 trace volume도 삭제한다. 기존
기록이 필요하지 않은 것이 확실할 때만 사용한다.

## Docker 주소를 혼동하기 쉬운 이유

현재 POC의 권장 실행은 다음 조합이다.

- Korean Chatbot FastAPI: Mac 호스트에서 실행
- LangFeather 대시보드: Docker에서 실행
- 연결 주소: `http://127.0.0.1:4319`

`127.0.0.1`은 각 프로세스가 실행되는 자기 공간을 뜻한다. 따라서 나중에 Korean
Chatbot FastAPI도 Docker 안에서 실행하면 그 컨테이너의 `127.0.0.1`은
LangFeather 컨테이너가 아니다. 그 단계에서는 두 서비스를 같은 Docker Compose
network에 넣고 `http://langfeather:4319`처럼 서비스 이름으로 연결해야 한다.
현재 프로젝트 Compose에는 아직 LangFeather 서비스를 합치지 않았다.

## 자주 확인할 문제

| 증상 | 확인할 내용 |
| --- | --- |
| `4319` 접속 실패 | Docker Desktop과 LangFeather 컨테이너 실행 여부 |
| 챗봇은 답하지만 trace가 없음 | `LANGFEATHER_ENABLED=true`로 FastAPI를 다시 시작했는지 |
| 예전 trace만 보임 | 질문 완료 후 화면 새로고침, endpoint가 `127.0.0.1:4319`인지 |
| LangSmith에도 trace가 생김 | 두 LangSmith tracing 변수를 `false`로 실행했는지 |
| Docker 안의 API에서 연결 실패 | `127.0.0.1` 대신 같은 network의 서비스 주소 필요 |

## LangFeather SDK를 업데이트한 경우

이 프로젝트는 항상 최신 `main`을 자동으로 가져오지 않고 검증한 LangFeather commit을
고정한다. 일반 사용자는 이 작업이 필요 없다. LangFeather SDK를 수정한 개발자가
새 버전을 이 프로젝트에서 검증할 때만 `<commit-sha>`를 실제 commit으로 바꿔
실행한다.

```bash
uv add \
  "langfeather[langchain] @ git+https://github.com/SungjinWi99/langfeather.git@<commit-sha>#subdirectory=sdk/python"
```

이 명령은 `pyproject.toml`과 `uv.lock`을 함께 갱신한다. 변경된 SDK와 이 프로젝트의
전체 테스트를 통과시킨 뒤 두 파일을 같은 변경 단위로 남긴다.
