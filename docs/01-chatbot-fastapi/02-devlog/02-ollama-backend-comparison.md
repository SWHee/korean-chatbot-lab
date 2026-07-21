# Ollama backend 전환과 HF Transformers 비교

- 작성일: 2026-07-04
- 현재 상태: Ollama를 기본 backend로 사용

## 해결하려던 문제

Hugging Face 모델이 FastAPI 프로세스 안에 있어 코드 수정 때마다 약 7.5GiB
가중치를 다시 적재해야 했다. 짧은 답변도 느려 개발 반복 속도가 떨어졌다.

모델 선택은 유지하면서 실행만 Ollama로 분리했다. 현재
[`ollama_generator.py`](../../../src/chatbot/ollama_generator.py)는 Ollama HTTP
API를 호출하고, FastAPI는 `CHATBOT_BACKEND` 환경 변수로 Ollama와 Hugging
Face 중 하나를 선택한다.

## 비교 방법

M2 Pro 16GB에서 인사, 적금 설명, 예금자보호제도, 금리 상식 질문 4개를 두
backend에 보냈다. 비교 당시 생성 상한은 둘 다 128 token이었고 warmup 후
측정했다. 두 런타임의 세부 디코딩 설정은 완전히 같지 않으므로 정밀한 모델
품질 실험이 아니라 개발 backend 선택을 위한 비교다.

## 결과

| 항목 | Ollama q4_K_M | HF FP16(MPS) |
| --- | ---: | ---: |
| 생성 속도 | 52~54 tok/s | 9~13 tok/s |
| 128 token 답변 | 2.65초 | 11~12초 |
| 모델 적재 | 약 3초 | 17.1초 |
| 가중치 상주 메모리 | 약 2.5GB | 약 7.5GiB |

코드 수정 후 FastAPI가 다시 응답하기까지 약 1.5초가 걸려, 프로세스 안에서
모델 전체를 다시 적재하던 구조보다 개발 반복이 빨라졌다. 네 질문에서는 4-bit
양자화로 인한 뚜렷한 한국어 품질 저하가 관찰되지 않았지만, 표본이 작으므로
양자화가 항상 무해하다는 의미는 아니다.

## 현재 설정

- 기본 backend: Ollama `qwen3:4b-instruct-2507-q4_K_M`
- Ollama 생성 상한: 1024 token
- Hugging Face 생성 상한: 128 token
- 공통 호출 경계: `generate(prompt)`, `stream(prompt)`

1024 token은 비교 실험 이후 Ollama 응답이 중간에 끊기는 문제를 줄이기 위해
올린 값이다. 따라서 위 속도 표의 128 token 실험 조건과 현재 설정을 구분해야
한다.

## 배운 점

- 같은 모델이라도 런타임과 양자화 방식에 따라 개발 경험이 크게 달라진다.
- 모델 서버를 FastAPI 밖으로 분리하면 API 코드 reload와 모델 수명을 분리할
  수 있다.
- 두 구현체를 endpoint에 직접 넣지 않고 같은 작은 경계를 유지해 backend
  변경이 API 코드에 퍼지지 않았다.
