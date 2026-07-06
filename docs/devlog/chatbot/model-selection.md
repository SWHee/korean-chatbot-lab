# 첫 주력 모델로 Qwen3 4B를 선택한 이유

- 작성일: 2026-06-29
- 현재 상태: Hugging Face 로컬 생성과 Ollama backend 구현 완료

## 해결하려던 문제

M2 Pro 16GB에서 실행할 수 있고 한국어 instruction 답변을 생성하는 모델이
필요했다. 로컬에서는 추론과 FastAPI 개발을 하고, 실제 파인튜닝이 필요해질
경우에만 Colab Pro+ GPU를 사용할 계획이었다.

후보를 비교할 때 다음 조건을 봤다.

- 한국어와 instruction-following 지원
- M2 Pro 16GB에서의 실행 가능성
- Hugging Face Transformers 호환성
- chat template와 라이선스
- 이후 RAG·파인튜닝으로 이어갈 수 있는가

## 후보와 장비 제약

| 후보 | 규모 | 판단 |
| --- | ---: | --- |
| `skt/A.X-4.0-Light` | 7B | 한국어 특화지만 원본 가중치가 로컬 메모리에 부담 |
| `Qwen/Qwen3-4B-Instruct-2507` | 4B | 원본 Transformers 흐름을 로컬에서 학습 가능한 범위 |
| `kakaocorp/kanana-1.5-2.1b-instruct-2505` | 2.1B | 실행 여유는 크지만 첫 주력 모델로 선택할 근거가 약함 |

가중치의 최소 메모리는 `parameter 수 × 자료형 크기`로 대략 계산할 수 있다.
BF16·FP16은 parameter당 2바이트이므로 4B는 약 7.5GiB, 7B는 약 13GiB다.
실제 실행에는 가중치 외에도 운영체제, PyTorch, 중간 계산과 KV cache 메모리가
필요하다. 따라서 16GB보다 작은 모델이라고 모두 안정적으로 실행되는 것은
아니다.

## 선택과 구현

첫 모델로 `Qwen/Qwen3-4B-Instruct-2507`을 선택했다. Apache 2.0이고,
`AutoTokenizer`, chat template, `AutoModelForCausalLM.generate()`를 사용하는
기본 Transformers 흐름을 직접 확인할 수 있기 때문이다.

현재 [`generator.py`](../../../src/chatbot/generator.py)는 다음을 수행한다.

1. tokenizer와 모델을 한 번 적재
2. MPS에서는 FP16, 그 외에는 FP32 사용
3. chat template 적용 후 tensor 생성
4. 입력 token을 제외하고 새 답변만 decode
5. 일괄 생성과 스트리밍 생성 제공

로컬 생성은 성공했지만 FastAPI 재시작 때마다 약 7.5GiB 모델을 다시 적재하고,
Transformers MPS 생성 속도도 느렸다. 이 문제는 모델 선택을 바꾸는 대신 같은
모델 계열의 Ollama backend를 추가해 해결했다. Hugging Face 구현은 모델 입력
과정을 직접 확인한 학습 결과이자 비양자화 비교 기준으로 남겨 둔다.

## 배운 점

- 모델 이름보다 parameter 수·자료형·실행 환경을 함께 봐야 한다.
- 모델이 지원하는 최대 context와 내 장비에서 사용할 수 있는 context는 다르다.
- 첫 구현에서는 원본 Transformers 흐름을 익히고, 실제 개발 병목이 확인된 뒤
  양자화 backend를 추가하는 순서가 복잡도를 줄였다.
- 이 선택은 Qwen3가 항상 가장 좋다는 뜻이 아니라 현재 장비와 학습 목표에 맞는
  출발점이라는 의미다.
