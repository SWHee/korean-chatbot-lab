# ADR 0005. PyTorch를 사용해 from-scratch 학습을 구현한다

- 상태: Accepted
- 날짜: 2026-06-24
- 관련 단계: `src/step03_tiny_model.py`, `src/step04_train_loop.py`

## 배경

이 프로젝트는 pretrained 모델을 바로 사용하는 대신 작은 한국어 언어 모델을
직접 만들고 학습시키는 과정을 목표로 한다. 다만 from-scratch의 의미가
"딥러닝 프레임워크 없이 모든 수식과 학습 과정을 직접 구현한다"는 뜻인지,
아니면 "pretrained weight 없이 모델 구조와 학습 루프를 직접 구성한다"는
뜻인지 명확히 할 필요가 있었다.

## 문제

PyTorch 같은 딥러닝 라이브러리를 사용하면 from-scratch라고 말하기 어려운지
혼란이 있었다. 반대로 PyTorch의 Dataset, DataLoader, nn.Module, loss,
optimizer 같은 기능까지 사용하지 않으면 실무적인 학습 흐름에서 멀어질 수
있다.

## 고려한 선택지

1. Python과 수식만으로 embedding, attention, backpropagation, optimizer까지 직접 구현한다.
2. PyTorch를 사용하되 pretrained weight 없이 모델 구조와 학습 루프를 직접 구성한다.
3. Hugging Face 같은 pretrained 모델을 가져와 fine-tuning 또는 inference 중심으로 진행한다.

## 결정

이 프로젝트의 from-scratch 기준은 "pretrained weight 없이 PyTorch로 모델
구조와 학습 루프를 직접 구성하고, 직접 준비한 corpus로 학습한다"로 정의한다.

## 결정 이유

- 실무와 학습 예제에서 PyTorch는 표준적인 딥러닝 구현 도구다.
- PyTorch를 사용해도 pretrained weight를 쓰지 않으면 모델은 랜덤 초기값에서 시작한다.
- `nn.Module`, `nn.Embedding`, `nn.TransformerEncoderLayer`, `CrossEntropyLoss`,
  optimizer, tensor, Dataset, DataLoader는 모델 학습을 구현하는 데 적절한 도구다.
- PyTorch 내부의 backpropagation이나 optimizer를 직접 재구현하는 것은 이 프로젝트의 목표가 아니다.
- 초반에 Python list로 원리를 확인한 뒤 PyTorch 방식으로 옮기면 개념 이해와 실무 감각을 함께 얻을 수 있다.

## 감수하는 단점

- PyTorch가 내부에서 처리하는 연산을 수식 수준으로 완전히 구현해보는 경험은 줄어든다.
- 라이브러리 호출만 보고 넘어가면 각 함수가 무엇을 대신 처리하는지 놓칠 수 있다.

## 나중에 다시 볼 조건

학습 루프가 완성된 뒤, 다음 항목을 설명할 수 있는지 확인한다.

- `nn.Embedding`이 token id를 vector로 바꾸는 이유
- `CrossEntropyLoss`가 logits와 target id를 비교하는 방식
- `loss.backward()`가 gradient를 계산하는 이유
- `optimizer.step()`이 weight를 업데이트하는 이유
- `Dataset`과 `DataLoader`가 batch 학습을 돕는 방식

설명이 부족한 부분은 별도 학습 노트나 작은 실험 코드로 보완한다.

## 결과 기록

초기 tokenizer와 dataset 원리는 Python list로 확인했다. 모델 정의와 학습
루프부터는 PyTorch를 적극적으로 사용한다. 이 방향은 "원리 이해"와 "실무적인
구현 방식" 사이의 균형을 맞추기 위한 선택이다.

