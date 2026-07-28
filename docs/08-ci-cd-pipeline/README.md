# Docker·EC2·CI/CD 실습

이 폴더는 FastAPI 서버를 Docker 이미지로 만들고 EC2에서 실행한 뒤, 같은 일을
GitHub Actions로 자동화한 과정을 기록한다.

## 이번 실습에서 사용하는 이미지

이미지는 두 개다.

| 이미지 | 누가 만드나 | 역할 |
| --- | --- | --- |
| `사용자명/korean-chatbot` | 우리가 Dockerfile로 생성 | FastAPI 서버 |
| `ollama/ollama` | Docker Hub에서 pull | Qwen3 모델 실행 |

두 이미지로 FastAPI 컨테이너와 Ollama 컨테이너를 하나씩 실행한다.
`docker-compose.yml`은 두 컨테이너를 함께 켜고 연결하는 파일이다.

## 문서

- [`01-challenge-workflow.md`](01-challenge-workflow.md): 처음부터 자동 배포까지의 순서
- `02-devlog/`: 실제로 실행해 본 뒤 작업일지를 추가할 위치

## 작업일지를 남기는 시점

매 명령마다 기록하지 않고 다음 세 작업이 끝날 때 한 번씩 남긴다.

1. 로컬에서 Docker Compose 실행 완료
2. EC2에서 수동 실행과 외부 접속 완료
3. GitHub Actions 자동 배포 완료

작업일지는 다음 내용을 쉬운 말로 적는다.

```text
# 이번에 해본 것

## 목표
어디까지 해보려고 했는지

## 실행
중요한 명령과 확인 결과

## 막힌 부분
어떤 오류가 있었는지

## 해결
원인이 무엇이었고 어떻게 고쳤는지

## 다음 작업
이어서 할 내용
```

실제로 겪지 않은 오류나 결과는 미리 작성하지 않는다.
