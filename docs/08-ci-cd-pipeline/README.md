# Docker·EC2·CI/CD 챌린지

현재 멀티턴 Agent를 Docker Compose로 실행하고, 같은 이미지를 EC2와 GitHub Actions에서
배포하기 위한 문서다.

## 현재 기준선

```text
브라우저 → web(Next.js) → api(FastAPI·LangGraph)
                              ├─ Claude API
                              ├─ Finlife API
                              ├─ KURE·Chroma
                              └─ SQLite thread
```

| 프로젝트 이미지 | 역할 | 외부 공개 |
| --- | --- | --- |
| `korean-chatbot-web` | 상담 화면과 API proxy | EC2 `3000` |
| `korean-chatbot-api` | Agent·검색·외부 API 연결 | 공개하지 않음 |

Ollama는 자동 fallback이 아니므로 배포에서 제외했다. LangFeather와 평가 실행도 사용자
질문 경로가 아니어서 띄우지 않는다.

## 현재 진행 상태

- 완료: Agent 기준 Dockerfile·Compose 재작성과 로컬 이미지 build
- 완료: GitHub Actions의 테스트·두 이미지 발행·EC2 갱신 설정
- 완료: Docker Hub 수동 발행, Seoul EC2 최초 index 생성, 공인 IP `:3000` 공개 확인
- 완료: GitHub Actions용 Docker Hub·EC2 Secrets 등록
- 다음: 현재 HTTP 수정 commit·push로 첫 GitHub Actions 자동 배포 확인

## 문서 읽는 순서

1. [`04-agent-deployment-design.md`](04-agent-deployment-design.md): 무엇을 왜 배포하는지
2. [`01-challenge-workflow.md`](01-challenge-workflow.md): 실제 실행 명령과 문법 설명
3. [`02-devlog/02-agent-deployment-runtime.md`](02-devlog/02-agent-deployment-runtime.md):
   이번 재작성에서 바뀐 점과 확인 결과
4. [`03-model-backend-options.md`](03-model-backend-options.md): Ollama를 제외한 결정

과거 Ollama Compose 실습은
[`02-devlog/01-minimal-deployment-runtime.md`](02-devlog/01-minimal-deployment-runtime.md)에
그 당시 확인한 사실로 보존한다.

구현 단계의 체크리스트는
[`05-agent-deployment-implementation-plan.md`](05-agent-deployment-implementation-plan.md)에
있다.
