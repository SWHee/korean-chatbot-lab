# From Scratch와 PyTorch 사용 기준

이 문서는 from-scratch 모델을 만들면서 PyTorch를 어디까지 사용해도 되는지
헷갈렸던 부분을 정리한 학습 노트다.

## 처음 헷갈렸던 점

from-scratch 모델이라는 말 때문에 pretrained 모델을 쓰지 않는다는 것은
이해하고 있었다. 하지만 PyTorch 같은 딥러닝 라이브러리까지 최대한 쓰지
않아야 포트폴리오에서 더 강점이 되는지 헷갈렸다.

특히 다음과 같은 의문이 있었다.

- PyTorch의 Dataset, DataLoader를 쓰면 from-scratch가 아닌가?
- `nn.Module`을 상속받아 모델을 정의하면 직접 만든 모델이라고 할 수 있는가?
- `CrossEntropyLoss`, `backward`, optimizer를 쓰는 것이 너무 라이브러리에 의존하는 것은 아닌가?
- 초보자인 내가 PyTorch 내부 기능을 라이브러리 개발자처럼 직접 구현하려는 것은 아닌가?

## 정리한 기준

이 프로젝트에서 from-scratch는 다음 의미로 사용한다.

```text
pretrained weight를 가져오지 않는다.
모델 구조를 직접 정의한다.
학습 루프를 직접 구성한다.
내 corpus로 직접 학습시킨다.
```

반대로 다음을 모두 직접 구현한다는 뜻은 아니다.

```text
행렬 곱셈 직접 구현
softmax 직접 구현
backpropagation 직접 구현
optimizer 직접 구현
PyTorch Dataset/DataLoader를 끝까지 사용하지 않기
Transformer attention을 모든 수식부터 직접 구현하기
```

그렇게 하면 한국어 챗봇 모델 프로젝트가 아니라 딥러닝 프레임워크 구현
프로젝트에 가까워진다.

## PyTorch를 쓰는 이유

PyTorch는 모델을 만들고 학습시키기 위한 표준적인 도구다. 실무와 예제 코드도
대부분 PyTorch 또는 비슷한 프레임워크를 사용한다.

이 프로젝트에서는 PyTorch를 다음 용도로 사용한다.

- `torch.Tensor`: 숫자 데이터를 모델 계산에 맞는 형태로 표현
- `nn.Module`: 모델 구조 정의
- `nn.Embedding`: token id를 vector로 변환
- `nn.TransformerEncoderLayer`: Transformer block 구성
- `nn.Linear`: 다음 token 후보 점수인 logits 출력
- `CrossEntropyLoss`: logits와 정답 token id 비교
- `loss.backward()`: gradient 계산
- `optimizer.step()`: weight 업데이트
- `Dataset`, `DataLoader`: 학습 예제를 batch 단위로 공급

## 지금까지 Python list로 직접 본 이유

초반에 Python list로 tokenizer와 dataset 원리를 본 이유는 PyTorch를 피하기
위해서가 아니다. 내부 흐름을 눈으로 보기 위해서다.

예를 들어 dataset 단계에서 먼저 다음 구조를 확인했다.

```text
[10, 20, 30, 40]

x = [10, 20, 30]
y = [20, 30, 40]
```

이것을 이해한 뒤 PyTorch Dataset/DataLoader로 옮기면, DataLoader가 마법처럼
보이지 않는다. 결국 DataLoader도 이런 input/target 예제를 여러 개 묶어
batch로 제공하는 도구이기 때문이다.

## 앞으로의 진행 기준

앞으로는 다음 균형을 따른다.

```text
원리를 처음 확인할 때:
    Python list와 작은 예시로 직접 본다.

실제 모델과 학습을 구현할 때:
    PyTorch를 적극적으로 사용한다.
```

구체적으로는:

- Step 1 tokenizer: 직접 구현 유지
- Step 2 dataset: list로 원리 확인 후 tensor, Dataset, DataLoader로 확장
- Step 3 model: PyTorch `nn.Module`로 정의
- Step 4 train loop: PyTorch loss, backward, optimizer 사용
- Step 5 generate: `model.eval()`, `torch.no_grad()` 사용
- Step 6 FastAPI: 모델을 웹 API로 감싸기

## 기억할 문장

PyTorch를 쓰는 것은 from-scratch와 모순되지 않는다.  
pretrained weight 없이 모델 구조와 학습 루프를 직접 구성하고, 내 데이터로
학습시키면 이 프로젝트에서는 from-scratch 모델이라고 볼 수 있다.

중요한 것은 PyTorch를 안 쓰는 것이 아니라, PyTorch가 무엇을 대신 처리해주는지
알고 사용하는 것이다.

