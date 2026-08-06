# Agent POC 배포 설계

- 작성일: 2026-08-06
- 목표: 현재 멀티턴 Agent를 로컬 Compose와 EC2에서 같은 구조로 실행

## 배포 기준

기본 배포는 `web`과 `api` 두 service만 사용한다.

```text
브라우저
  → Next.js web :3000
  → FastAPI api :8000
  → Claude API
  ├─ KURE·Chroma 법령 검색
  ├─ Finlife 상품 조회
  └─ SQLite 대화 상태 저장
```

Ollama는 자동 fallback이 아니므로 배포에서 제외한다. 기존 Ollama 코드는 로컬 모델
비교용으로만 보존한다. Anthropic 호출 실패 시 Ollama로 바꾸지 않고 Agent 오류로
처리한다.

## 파일별 책임

| 파일 | 책임 |
| --- | --- |
| `Dockerfile` | FastAPI 코드와 운영 의존성을 API 이미지로 묶음 |
| `frontend/Dockerfile` | Next.js production server를 web 이미지로 묶음 |
| `.dockerignore` | secret, SQLite, cache처럼 이미지에 들어가면 안 되는 파일 제외 |
| `docker-compose.yml` | web·api 연결, 환경 변수와 보존 volume 정의 |
| `.github/workflows/deploy.yml` | 검사, 두 이미지 발행, EC2 컨테이너 갱신 |

## 환경 변수와 데이터

API 컨테이너에는 다음 값을 실행 시점에 전달한다.

- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`: Agent 분석·Tool 선택·답변 생성
- `FINLIFE_API_KEY`: 정기예금 상품 조회
- `CHATBOT_INDEX_DIR`: Chroma 인덱스 위치

실제 key는 이미지와 GitHub Actions 파일에 쓰지 않는다. 로컬과 EC2의 Git 제외
`.env`에 한 번 준비하고 Compose가 읽는다.

컨테이너 교체 후에도 다음 데이터는 남긴다.

- `./data/index`: 다시 만들 수 있지만 생성 시간이 긴 Chroma 인덱스
- `huggingface_cache`: KURE 모델 다운로드 cache
- `agent_runtime`: 멀티턴 대화를 저장하는 SQLite 파일

`.runtime`은 로컬 Docker build context에서도 제외해 기존 대화가 이미지에 복사되지
않게 한다.

## 자동 배포 흐름

```text
main push
  → Python 테스트
  → Next.js production build
  → api·web 이미지 build/push
  → EC2에 최신 Compose 복사
  → api·web pull 및 재시작
  → 컨테이너 상태와 web HTTP 응답 확인
```

EC2의 `.env`, Chroma 인덱스와 named volume은 자동 배포 전에 한 번 준비한다. 매 push
때 API key나 인덱스를 다시 만들지 않는다.

## 완료 기준

1. Compose 결과에 `web`, `api`만 존재
2. 이미지 안에 `.env`와 `.runtime/langgraph.sqlite3`가 없음
3. 법령 질문과 Finlife 상품 질문이 Agent UI에서 완료
4. 같은 thread의 후속 질문이 컨테이너 재생성 후에도 이어짐
5. GitHub Actions 배포 후 EC2의 `http://127.0.0.1:3000` 응답 성공

HTTPS·도메인·무중단 배포·자동 Ollama fallback은 이번 POC에서 제외한다.
