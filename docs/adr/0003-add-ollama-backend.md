# ADR 0003. 개발·서빙 backend로 Ollama를 추가한다

- 상태: Accepted
- 날짜: 2026-07-04
- 구현 상태: In progress

## 배경

현재 챗봇은 `Qwen/Qwen3-4B-Instruct-2507`을 Transformers와 PyTorch MPS로
FastAPI 프로세스 안에 직접 적재한다(ADR 0002). 생성과 스트리밍, FastAPI
서빙까지 동작을 확인했고, 다음 단계로 LangChain 연결과 RAG를 준비하고 있다.

이 구조에서 개발 반복 속도에 두 가지 문제가 확인되었다.

- 모델이 FastAPI 프로세스 안에 있으므로 `--reload`를 사용할 수 없다. 코드가
  바뀔 때마다 프로세스가 재시작되고 약 7.5GiB 가중치를 다시 적재해야 한다.
- Transformers의 MPS 추론은 범용 커널이라 Apple Silicon에서 느리다. 짧은
  인사 prompt에도 응답까지 약 20초가 걸린다.

ADR 0001은 다른 backend를 "실제 비교 필요가 생길 때" `Generator` 경계의
adapter로 추가하기로 했다. 개발 반복 속도라는 실제 필요가 생겼다.

## 고려한 선택지

1. 현재 구조를 유지하고 재시작 시 재적재를 감수한다.
2. Transformers 모델을 별도 Python 프로세스로 분리해 자체 모델 서버를 만든다.
3. Ollama를 모델 서버로 사용하고 `Generator`의 두 번째 구현체로 연결한다.

선택지 2는 프로세스 분리로 `--reload` 문제는 해결하지만, 느린 Transformers
MPS 추론이 그대로 남고 모델 적재·상주·API 코드를 직접 유지해야 한다.
Ollama가 이미 제공하는 기능을 더 느린 런타임 위에 다시 만드는 셈이다.

## 결정

Ollama를 로컬 개발·서빙 backend로 추가한다. Ollama library의
`qwen3:4b-instruct-2507`(q4_K_M 양자화, 약 2.5GB)을 사용해 ADR 0002의 모델
선택을 유지한다.

`Generator`와 같은 인터페이스(`generate`, `stream`)를 갖는 두 번째 구현체를
만들고, FastAPI는 환경 변수 하나로 backend를 선택한다. registry나 factory는
만들지 않는다.

기존 Hugging Face `Generator`는 삭제하지 않는다. tokenizer, chat template,
tensor, device 처리를 직접 다룬 학습 결과이자 비양자화 fp16 기준점으로
유지하고, 같은 prompt로 양자화 모델과 품질을 비교할 때 사용한다.

## 결정 이유

- 모델이 Ollama 데몬으로 분리되면 FastAPI 프로세스가 가벼운 HTTP 클라이언트가
  되어 `--reload`를 자유롭게 사용할 수 있다.
- Ollama는 llama.cpp의 Metal 최적화 커널과 4-bit 양자화를 사용해 Transformers
  MPS 대비 생성 속도가 크게 빠르다.
- 가중치 상주 메모리가 약 7.5GiB에서 약 2.5GB로 줄어 RAG 단계에서 임베딩
  모델을 올릴 메모리 여유가 생긴다.
- 같은 체크포인트 계열을 사용하므로 모델 선택(ADR 0002)을 바꾸지 않는다.
- LangChain에 `langchain-ollama` 공식 통합이 있어 다음 단계와 연결이 쉽다.
  다만 핵심 경계는 계속 프로젝트 소유의 `Generator`로 유지한다.
- ADR 0001이 예정한 "실제 비교 필요가 생길 때 adapter 추가"에 해당하므로
  경계 설계를 바꾸지 않고 구현체만 추가한다.

## 감수하는 단점

- q4_K_M 양자화로 한국어 답변 품질이 fp16과 미세하게 달라질 수 있다. 같은
  prompt로 비교해 확인하고, 필요하면 q8_0(약 4.3GB)으로 조정한다.
- chat template 적용과 생성 내부가 Ollama 뒤로 가려진다. 해당 학습은 Hugging
  Face 트랙에서 이미 완료했으므로 손실로 보지 않는다.
- 로컬에 Ollama 데몬이라는 실행 의존성이 추가된다.
- 기본 설정은 유휴 5분 후 모델을 내리므로 상주가 필요하면 `keep_alive`
  설정이 필요하다.

## 검증 계획

같은 한국어 인사 prompt로 smoke test를 수행하고 현재 Transformers 경로의 약
20초와 응답 시간을 비교한다. 두 번째 구현체가 동작하면 `/chat`과
`/chat/stream`이 기존과 같은 형식으로 응답하는지 확인하고, 품질·속도 비교는
별도 devlog로 남긴다.
