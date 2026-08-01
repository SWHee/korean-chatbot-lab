# LangFeather 0.2.0 개인 실행 안내

LangFeather는 이 프로젝트의 선택적 로컬 추적 도구다. collector를 EC2나 외부에
공개하지 않고, 개인 컴퓨터에서만 실행한다.

## 1. collector와 SDK 준비

Docker Desktop을 실행한 뒤 공개 이미지를 내려받아 collector를 시작한다. LangFeather
저장소를 clone하거나 이미지를 직접 build하지 않는다.

```bash
docker pull ghcr.io/sungjinwi99/langfeather:0.2.0

docker run -d --name langfeather \
  -p 127.0.0.1:4319:4319 \
  -v langfeather-data:/data \
  ghcr.io/sungjinwi99/langfeather:0.2.0
```

Korean Chatbot 저장소에서는 PyPI의 Python SDK를 설치한다.

```bash
uv sync --group tracing
```

GitHub Container Registry는 완성된 Docker 이미지를 보관한다. collector는 사용자의
Docker에서 실행되고 trace는 `langfeather-data`라는 로컬 Docker volume에 저장된다.
GitHub 저장소나 외부 서버에 trace를 저장하는 구조가 아니다.

health와 화면을 확인한다.

```bash
curl --fail http://127.0.0.1:4319/api/v1/health
```

- 대시보드: `http://127.0.0.1:4319`
- 계정·API key: 필요 없음

## 2. 호스트에서 FastAPI와 추적 실행

FastAPI를 Mac 호스트에서 실행할 때 collector 주소는 `127.0.0.1:4319`다.

```bash
LANGFEATHER_ENABLED=true \
LANGFEATHER_ENDPOINT=http://127.0.0.1:4319 \
uv run --group tracing fastapi dev
```

질문을 보낸 뒤 대시보드에서 `korean-chatbot-rag` trace를 선택한다. 최상위
LangGraph 아래의 `retrieve`, `generate` 실행과 입출력을 확인할 수 있다.

LangSmith를 함께 켜고 싶으면 기존 `LANGSMITH_TRACING=true` 설정을 유지한다. 두 도구는
서로를 대체하거나 설정을 덮어쓰지 않으며, 같은 실행을 각자의 저장소에 추적할 수
있다. LangFeather만 확인하려면 해당 실행에서 LangSmith를 별도로 끈다.

## 3. Docker 주소 구분

`127.0.0.1`은 현재 프로세스가 실행되는 자기 컴퓨터나 컨테이너를 가리킨다.

- FastAPI가 호스트에서 실행: `http://127.0.0.1:4319`
- FastAPI도 Docker Desktop 컨테이너에서 실행: 컨테이너의 `127.0.0.1`은 collector가 아님

현재 기본 `docker-compose.yml`은 운영·EC2 배포 경계이므로 LangFeather SDK와
collector를 포함하지 않고 `LANGFEATHER_ENABLED=false`를 유지한다. 따라서 기본
Compose에서 임의로 tracing을 켜지 않는다.

Mac Docker Desktop에서 별도로 tracing SDK가 포함된 API 컨테이너를 준비한 경우에는
호스트 collector에 `http://host.docker.internal:4319`로 접근할 수 있다. 이는 현재
Mac 개발 환경용 주소이며 EC2나 일반 Linux Docker에 그대로 적용하지 않는다.
LangFeather collector를 기본 Compose service로 추가하거나 public EC2에 공개하지
않는다.

## 4. 종료와 데이터

FastAPI는 종료할 때 SDK의 대기 중인 trace 전송을 마무리한다. 계속 실행되는 서버에서
요청마다 `flush()`를 호출하지 않는다.

collector만 멈추고 trace volume을 보존한다.

```bash
docker stop langfeather
```

다시 시작할 때는 다음 명령을 사용한다.

```bash
docker start langfeather
```

`docker rm`이나 volume 삭제는 기존 trace가 필요하지 않은 경우에만 별도로 수행한다.

## 자주 확인할 문제

| 증상 | 확인할 내용 |
| --- | --- |
| `4319` 접속 실패 | Docker Desktop과 `langfeather` 컨테이너 실행 여부 |
| 챗봇은 답하지만 trace가 없음 | `LANGFEATHER_ENABLED=true`로 FastAPI를 다시 시작했는지 |
| 호스트 API에서 연결 실패 | endpoint가 `http://127.0.0.1:4319`인지 |
| Docker API에서 연결 실패 | 컨테이너 안의 `127.0.0.1`을 사용하지 않았는지 |
| LangSmith에도 trace가 생김 | 두 추적 도구를 함께 활성화한 정상 결과인지 |
