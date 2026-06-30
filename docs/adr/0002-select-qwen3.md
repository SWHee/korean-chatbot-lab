# ADR 0002. 첫 모델로 Qwen3 4B를 선택한다

- 상태: Accepted
- 날짜: 2026-06-30
- 구현 상태: Not started

## 배경

주력 챗봇은 로컬 Hugging Face instruction-tuned 모델로 시작한다. 첫 구현에서는
tokenizer, chat template, tensor, `generate()`와 device 처리를 직접 확인하고,
이후 같은 생성 기능을 FastAPI와 LangChain에서 사용할 계획이다.

사용할 수 있는 환경은 M2 Pro 16GB 맥북과 Colab Pro+다. 맥북에서는 로컬 추론과
애플리케이션 개발을 진행하고, 파인튜닝이 필요해지면 Colab GPU에서 LoRA 또는
QLoRA를 사용할 계획이다.

## 고려한 선택지

1. `skt/A.X-4.0-Light`
2. `Qwen/Qwen3-4B-Instruct-2507`
3. `kakaocorp/kanana-1.5-2.1b-instruct-2505`

A.X 4.0 Light는 한국어 특화 성능과 라이선스가 좋지만 7B BF16 가중치만 약
13GiB이므로 16GB 통합 메모리에서 원본 Transformers 모델을 안정적으로 실행하기
어렵다. Kanana 1.5 2.1B는 로컬 실행에 여유가 있지만 생성 품질과 향후 agent
실험을 함께 고려하면 첫 주력 모델로 선택할 이유가 상대적으로 적었다.

## 결정

첫 모델로 `Qwen/Qwen3-4B-Instruct-2507`을 사용한다.

맥북에서는 Hugging Face의 BF16 checkpoint를 Transformers와 PyTorch MPS로 직접
불러오는 흐름부터 구현한다. 양자화는 초기 필수 조건으로 두지 않는다. A.X 4.0
Light는 생성 경계와 서빙 흐름을 만든 뒤 한국어 품질 비교가 필요할 때 다시
검토한다.

## 결정 이유

- 4B BF16 가중치는 약 7.5GiB로 짧은 context에서 M2 Pro 16GB로 검증해 볼 수 있는
  범위다.
- `AutoTokenizer`와 `AutoModelForCausalLM`을 사용하는 기본 Transformers 흐름을
  그대로 학습할 수 있다.
- 한국어를 지원하고 instruction-following과 tool calling을 위한 chat template가
  제공된다.
- Apache 2.0 라이선스로 포트폴리오와 향후 활용에 제약이 적다.
- LoRA와 QLoRA 자료 및 생태계가 풍부해 이후 파인튜닝 단계로 이어가기 쉽다.
- 로컬 추론과 Colab 학습이 같은 Transformers 계열 코드에 머물러 초기 복잡도가
  낮다.

## 감수하는 단점

- 한국어에 특화된 모델이 아니므로 A.X보다 한국어 답변 품질이 낮을 수 있다.
- M2 통합 메모리에서 실제로 적재되는지는 아직 확인하지 않았다.
- 모델이 지원하는 최대 context를 로컬 환경에서 그대로 사용할 수 없다.
- 향후 품질 문제가 확인되면 양자화 모델 또는 다른 backend를 비교해야 한다.

## 검증 계획

현재 단계에서는 공개 벤치마크를 반복하지 않는다. Python 3.13 환경에서 tokenizer와
chat template를 확인하고, 모델을 MPS에 적재한 뒤 한국어 prompt 한 건을 생성하는
smoke test를 수행한다.

파인튜닝 목표와 데이터셋이 정해지면 별도의 평가 세트를 만들고, 같은 평가 세트로
기본 모델과 파인튜닝 모델을 비교한다.
