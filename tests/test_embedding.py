import torch

from chatbot.embedding import MODEL_NAME, embed_texts


class FakeEncoder:
    """모델 다운로드 없이 encode 인터페이스 재현 + 호출 인자 기록"""

    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append(kwargs)
        return torch.ones(len(texts), 4)


def test_model_name_is_kure() -> None:
    """ADR 0005 선정 모델 고정"""
    assert MODEL_NAME == "nlpai-lab/KURE-v1"


def test_embed_texts_returns_vector_per_text() -> None:
    """입력 개수만큼 벡터 목록 반환 + 정규화·배치 계약 전달"""
    encoder = FakeEncoder()
    vectors = embed_texts(encoder, ["질문", "조문", "청크"])
    assert len(vectors) == 3
    assert all(isinstance(v, list) and len(v) == 4 for v in vectors)
    assert encoder.calls == [{"batch_size": 16, "normalize_embeddings": True}]
