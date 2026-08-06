# 배포 생성 모델 결정

- 최초 작성: 2026-07-30
- 결정 갱신: 2026-08-06

## 결정

현재 Agent POC 배포는 Anthropic Claude를 사용하고 Ollama container는 제외한다.

```text
이전 RAG 실습: FastAPI → Docker Ollama → Qwen3
현재 Agent:     FastAPI → Anthropic API → Claude
```

현재 Ollama 구현은 `CHATBOT_BACKEND=ollama`를 선택할 수 있지만, Anthropic 호출 실패를
감지해 Ollama로 자동 전환하는 fallback은 구현되어 있지 않다. Agent의 Tool Calling
모델도 Claude를 직접 사용한다. 따라서 두 모델을 함께 띄우면 장애 대응은 되지 않고
EC2 메모리·디스크만 더 사용한다.

## 배포에서 달라진 점

- `ollama` service와 Qwen model volume 제거
- API 컨테이너에 `ANTHROPIC_API_KEY`, `FINLIFE_API_KEY` 전달
- 일반 CPU EC2에서도 로컬 생성 모델을 메모리에 올리지 않음
- 모델 weight 대신 질문별 API 사용료 발생
- 인터넷 연결, 공급자 사용량 제한과 장애의 영향을 받음

KURE 임베딩과 Chroma 검색은 EC2 API 컨테이너에서 계속 실행된다. 따라서 PyTorch,
Transformers와 Hugging Face cache까지 없어지는 것은 아니다.

## 보존하는 범위

Ollama 코드와 과거 결과는 오픈웨이트 모델 비교·학습 자료로 유지한다. 다시 배포 후보로
검토하려면 다음을 먼저 구현하고 별도 Compose로 검증한다.

1. Agent Tool Calling을 지원하는 Ollama 모델 경로
2. 어떤 오류에서 전환할지 정한 fallback 정책
3. 같은 요청의 중복 실행과 Tool 재호출 방지
4. EC2 메모리·응답 시간·모델 저장 공간 비교

현재 CI/CD 챌린지에는 이 범위를 포함하지 않는다.
