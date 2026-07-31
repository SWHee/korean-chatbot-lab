# Docker·EC2·CI/CD 챌린지

이 폴더는 현재 프로젝트 전체를 Docker Compose로 실행하고, 같은 구성을 EC2와
GitHub Actions 배포까지 이어 가는 과정을 기록한다.

## 진행 원칙

이번 챌린지는 확인용 컨테이너를 잠깐 띄운 뒤 버리는 방식으로 진행하지 않는다.
현재 구현을 기준으로 최종 실행 구조를 먼저 정하고, 같은 Dockerfile·Compose·workflow를
단계마다 보강한다.

```text
실행 계약 확정
  → 백엔드 이미지 완성
  → 프론트엔드 이미지 완성
  → 전체 Compose 완성
  → EC2 수동 배포
  → GitHub Actions 자동 배포
```

각 단계의 검증은 다음 파일을 다시 만들기 위한 임시 실험이 아니라, 최종 구성에
그대로 남길 설정이 맞는지 확인하는 체크포인트다.

## 현재 배포 기준선

미래 계획이 아니라 지금 실제로 동작하는 구성만 포함한다.

현재 로컬 Compose의 전체 질문 경로까지 확인했다. 다음 단계는 API·web 이미지를
Docker Hub에 수동으로 올리고 다시 내려받는 검증이다.

| 이미지 | 준비 방법 | 역할 |
| --- | --- | --- |
| `korean-chatbot-api` | 프로젝트에서 build | FastAPI·LangGraph·RAG |
| `korean-chatbot-web` | 프로젝트에서 build | Next.js 상담 UI와 API proxy |
| `ollama/ollama` | Docker Hub에서 pull | Qwen3 모델 실행 |

프로젝트가 직접 만드는 이미지는 2개이고, 전체 Compose가 사용하는 이미지는 3개다.
Chroma 인덱스, Hugging Face cache, Ollama 모델은 컨테이너 교체 후에도 남아야 하는
실행 데이터로 다룬다.

LangFeather는 선택적 로컬 추적 기능이므로 기본 배포에서 제외한다. 아직 구현하지 않은
Finlife Agent도 미리 넣지 않고, 실제 코드가 배포 기준선에 들어온 뒤 갱신한다.

## 문서

- [`01-challenge-workflow.md`](01-challenge-workflow.md): 누적형 구현 순서와 완료 기준
- [`02-devlog/01-minimal-deployment-runtime.md`](02-devlog/01-minimal-deployment-runtime.md):
  UI·RAG 시연에 필요한 컨테이너 경계, 로컬 Compose 결과와 속도 차이
- [`03-model-backend-options.md`](03-model-backend-options.md):
  Docker Ollama 대신 외부 모델 API를 사용할 때 달라지는 부분

## 작업일지를 남기는 시점

다음 결과가 완성될 때 한 번씩 기록한다.

1. ~~백엔드·프론트엔드 이미지와 전체 로컬 Compose 검증~~
2. Docker Hub 발행과 EC2 전체 서비스 수동 배포
3. GitHub Actions로 두 이미지를 자동 갱신하고 EC2 재배포

각 기록에는 목표, 실제 명령, 막힌 증상, 원인, 해결, 확인 결과와 다음 작업만 남긴다.
실제로 겪지 않은 실패나 결과는 미리 작성하지 않는다.
