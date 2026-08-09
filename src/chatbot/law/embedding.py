"""법령 청크 임베딩 (ADR 0005: KURE-v1)"""

from sentence_transformers import SentenceTransformer

# 인덱싱과 질의 임베딩은 반드시 같은 모델·전처리·정규화·backend 사용
MODEL_NAME = "nlpai-lab/KURE-v1"
EMBEDDING_BATCH_SIZE = 16


def load_encoder(device: str | None = None) -> SentenceTransformer:
    """선정 모델 로드 (KURE-v1: prefix 불필요, 1024차원, 8192토큰)"""
    return SentenceTransformer(MODEL_NAME, device=device)


def embed_texts(
    encoder: SentenceTransformer,
    texts: list[str],
) -> list[list[float]]:
    """텍스트 목록 → 정규화된 1024차원 벡터 목록"""
    embeddings = encoder.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        normalize_embeddings=True,
    )
    return embeddings.tolist()
