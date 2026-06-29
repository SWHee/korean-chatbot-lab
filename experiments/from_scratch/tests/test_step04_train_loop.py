"""Step 04 학습 루프의 작은 단위 테스트."""

import torch
from torch import nn

from step04_train_loop import calculate_loss


def test_calculate_loss_returns_scalar_tensor() -> None:
    """여러 토큰의 예측값을 하나의 loss 값으로 계산하는지 확인한다."""

    logits = torch.tensor(
        [
            [
                [0.1, 2.0, 0.3],
                [0.2, 0.4, 1.8],
            ]
        ]
    )
    target_ids = torch.tensor([[1, 2]])
    loss_function = nn.CrossEntropyLoss()

    loss = calculate_loss(logits, target_ids, loss_function)

    assert loss.ndim == 0
    assert torch.isfinite(loss)
