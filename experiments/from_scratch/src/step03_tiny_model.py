"""Step 03. 작은 모델.

역할:
    PyTorch로 아주 작은 from-scratch Transformer 언어 모델을 정의한다.

학습 포인트:
    - 토큰 임베딩(token embedding),
    - 위치 정보(positional information),
    - causal self-attention,
    - 다음 토큰 예측을 위한 vocabulary logits,
    - 모델 내부를 흐르는 텐서 shape 이해하기.

나중의 프로젝트 구조:
    모델 구조와 사용 방식이 안정되면 이 파일은 `model.py`가 될 수 있다.
"""

import torch
from torch import nn


def create_causal_mask(context_size: int) -> torch.Tensor:
    """미래 토큰을 보지 못하게 막는 causal mask를 만든다.

    언어 모델은 다음 토큰을 예측해야 하므로, 현재 위치에서 미래 위치의
    정답을 미리 보면 안 된다.
    """

    mask = torch.zeros(context_size, context_size)

    for row_index in range(context_size):
        for column_index in range(context_size):
            is_future_position = column_index > row_index

            if is_future_position:
                mask[row_index, column_index] = float("-inf")

    return mask


class TinyTransformerLanguageModel(nn.Module):
    """작은 Transformer 기반 언어 모델.

    이 모델의 목표는 좋은 성능이 아니라, 언어 모델의 기본 구성 요소를
    직접 이해하는 것이다.
    """

    def __init__(
        self,
        vocab_size: int,
        context_size: int,
        embedding_dim: int = 32,
        num_heads: int = 4,
        num_layers: int = 2,
    ) -> None:
        """모델에 필요한 층들을 준비한다."""

        super().__init__()

        self.vocab_size = vocab_size
        self.context_size = context_size
        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.num_layers = num_layers

        self.token_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.position_embedding = nn.Embedding(context_size, embedding_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embedding_dim,
            nhead=num_heads,
            batch_first=True,
            dropout=0.0,
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer=encoder_layer,
            num_layers=num_layers,
        )
        self.output_layer = nn.Linear(embedding_dim, vocab_size)

        causal_mask = create_causal_mask(context_size)
        self.register_buffer("causal_mask", causal_mask)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        """token id를 입력받아 다음 토큰 예측용 logits를 반환한다."""

        batch_size, sequence_length = input_ids.shape

        if sequence_length > self.context_size:
            raise ValueError("입력 길이는 context_size보다 길 수 없다.")

        position_ids = torch.arange(sequence_length, device=input_ids.device)

        token_vectors = self.token_embedding(input_ids)
        position_vectors = self.position_embedding(position_ids)

        input_vectors = token_vectors + position_vectors

        attention_mask = self.causal_mask[:sequence_length, :sequence_length]
        hidden_states = self.transformer_encoder(
            input_vectors,
            mask=attention_mask,
        )
        logits = self.output_layer(hidden_states)

        return logits


def main() -> None:
    """작은 모델 파일의 뼈대가 준비됐는지 확인한다."""

    context_size = 4
    mask = create_causal_mask(context_size)
    model = TinyTransformerLanguageModel(
        vocab_size=20,
        context_size=context_size,
        embedding_dim=8,
    )
    input_ids = torch.tensor([[10, 11, 12, 13]])
    logits = model(input_ids)

    print(f"context_size: {context_size}")
    print("causal mask:")
    print(mask)
    print()
    print(f"input_ids shape: {input_ids.shape}")
    print(f"logits shape: {logits.shape}")


if __name__ == "__main__":
    main()
