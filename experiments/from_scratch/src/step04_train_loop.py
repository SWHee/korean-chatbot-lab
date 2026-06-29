"""Step 04. 학습 루프.

역할:
    작은 언어 모델을 학습시키고 loss가 줄어드는지 관찰한다.

학습 포인트:
    - forward pass,
    - loss 계산,
    - backward pass,
    - optimizer step,
    - 작은 모델이 작은 데이터셋에 먼저 overfit되는 이유 이해하기.

나중의 프로젝트 구조:
    학습 실행 방식이 실용적으로 정리되면 이 파일은 `train.py`가 되거나
    `scripts/train.py`로 이동할 수 있다.
"""

import torch
from torch import nn


def prepare_training_tensors() -> tuple[torch.Tensor, torch.Tensor, int]:
    """seed corpus를 읽어 학습용 input tensor와 target tensor를 만든다."""

    pass


def calculate_loss(
    logits: torch.Tensor,
    target_ids: torch.Tensor,
    loss_function: nn.Module,
) -> torch.Tensor:
    """모델 출력 logits와 정답 target_ids를 비교해 loss를 계산한다."""

    batch_size, sequence_length, vocabulary_size = logits.shape

    flat_logits = logits.reshape(
        batch_size * sequence_length,
        vocabulary_size,
    )
    flat_target_ids = target_ids.reshape(batch_size * sequence_length)

    loss = loss_function(flat_logits, flat_target_ids)

    return loss


def train_one_step(
    model: nn.Module,
    input_ids: torch.Tensor,
    target_ids: torch.Tensor,
    optimizer: torch.optim.Optimizer,
    loss_function: nn.Module,
) -> float:
    """학습을 한 번 수행하고 loss 값을 반환한다."""

    pass


def train() -> None:
    """작은 모델을 여러 번 학습시키고 loss 변화를 출력한다."""

    pass


def main() -> None:
    """학습 루프 파일의 뼈대가 준비됐는지 확인한다."""

    print("Step 04 train loop 함수 뼈대 준비 완료")
    print("다음 작업: calculate_loss()부터 구현")


if __name__ == "__main__":
    main()
