# Agent POC 배포 파일 재정리

- 작업일: 2026-08-06
- 목표: Ollama RAG 기준 배포를 현재 Claude 멀티턴 Agent 기준으로 갱신

## 왜 바꿨나

프론트는 이미 `/ask-agent/stream`을 사용하지만 Compose는 Ollama를 강제로 실행하고
Anthropic·Finlife key를 API에 전달하지 않았다. SQLite thread도 컨테이너 안에만 있어
이미지 갱신 시 사라질 수 있었다.

최근 프론트 개편에서는 실행 포트가 `3001`로 바뀌고 기존 Dockerfile도 사라졌다.
EC2 보안 그룹과 사용자 URL은 유지하기 위해 `3000:3001`로 연결했다.

## 파일별 변경

- `.dockerignore`: `.runtime`, SQLite와 로컬 산출물이 이미지에 들어가지 않게 제외
- `Dockerfile`: 의존성과 source 복사를 분리해 코드 변경 시 package layer 재사용
- `frontend/Dockerfile`: Next.js standalone production 이미지 복원, 내부 `3001` 사용
- `frontend/.dockerignore`: `.next`, `node_modules`, 개발 문서를 build context에서 제외
- `frontend/next.config.ts`: standalone server 출력 활성화
- `docker-compose.yml`: `web + api`, 외부 API key, Chroma·KURE·SQLite volume 연결
- `.github/workflows/deploy.yml`: 두 tag 발행, EC2 사전조건·health·HTTP 확인 추가

## 실제로 막힌 부분

첫 이미지 build는 `frontend/Dockerfile`이 없어서 바로 실패했다. 이전 CI/CD 문서는
프론트 개편 전 파일이 계속 존재한다고 가정하고 있었다. 현재 `package.json`의 `3001`
포트 계약을 확인한 뒤 Dockerfile과 standalone 설정을 새로 작성했다.

## 확인 결과

```bash
ANTHROPIC_API_KEY=test FINLIFE_API_KEY=test docker compose config --services
ANTHROPIC_API_KEY=test FINLIFE_API_KEY=test docker compose config --volumes
ANTHROPIC_API_KEY=test FINLIFE_API_KEY=test docker compose build api web
```

- service: `api`, `web`
- named volume: `huggingface_cache`, `agent_runtime`
- API와 web 이미지 build: 성공
- Python 테스트: 151개 통과, 외부 key가 필요한 2개 제외
- 프론트 테스트: 6개 통과
- Next.js production build: 성공
- API 이미지: 약 378MB, 외부 공개 포트 `8000`
- web 이미지: 약 66MB, 컨테이너 포트 `3001`
- 이미지 내부 `.env`, 기존 SQLite와 API key 흔적: 없음

placeholder key는 Compose 해석과 이미지 build에만 사용했으며 외부 API 요청은 보내지
않았다.

## 다음 수동 확인

실제 `.env`로 Compose를 올려 법령 질문과 Finlife 상품 두 턴을 확인했다. 두 이미지를
Docker Hub에 발행하고 EC2에서 index를 만든 뒤, 공인 IP의 `:3000`으로 공개 화면과
다중 턴 응답도 확인했다.

## 실제 EC2 배포에서 추가로 확인한 것

### 맥 이미지와 EC2 CPU가 달랐다

맥에서 일반 `docker compose build`로 올린 이미지는 `linux/arm64`였다. EC2는
`linux/amd64`라 `no matching manifest` 오류가 났다. 수동 발행은 아래처럼 플랫폼을
명시해야 했다.

```bash
docker buildx build --platform linux/amd64 --push ...
```

GitHub Actions도 같은 문제를 피하도록 두 이미지에 `platforms: linux/amd64`를 이미
지정했다.

### 공인 IP의 HTTP에서는 대화 ID 생성이 실패했다

`localhost`에서는 되던 `crypto.randomUUID()`가 `http://공인IP:3000`에서는 사용할 수
없어 화면 전체가 오류가 났다. `localhost`는 예외적으로 안전한 주소로 취급되지만 공인
IP HTTP는 아니다. `thread-id.ts`에서 UUID를 못 쓸 때 시간과 난수 조합을 만드는 작은
대체 값을 두었다. 대화 ID는 보안 토큰이 아니라 대화 구분용이므로 이 수준이면 충분하다.

### 자동 배포 전 준비

GitHub Actions Secret에 `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `EC2_HOST`,
`EC2_USERNAME`, `EC2_SSH_KEY`를 등록했다. EC2를 중지 후 다시 시작하면 공인 IP가
바뀌므로, 자동 배포 전 `EC2_HOST`도 새 IP로 갱신해야 한다.
