"""법령 청크 벡터스토어 접근 (ADR 0006: Chroma)"""

import os
from pathlib import Path

import chromadb

DEFAULT_INDEX_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "index"
    / "chroma"
)
COLLECTION_NAME = "statutes"


def resolve_index_dir() -> Path:
    """실행 환경별 Chroma 인덱스 경로"""
    configured_dir = os.getenv("CHATBOT_INDEX_DIR")
    return Path(configured_dir) if configured_dir else DEFAULT_INDEX_DIR


def open_collection(index_dir: str | Path | None = None):
    """persist된 인덱스 컬렉션 열기"""
    resolved_dir = Path(index_dir) if index_dir is not None else resolve_index_dir()
    client = chromadb.PersistentClient(path=str(resolved_dir))
    return client.get_collection(COLLECTION_NAME)


def search(collection, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """코사인 유사도 top-k 청크 반환 (본문 + 출처 메타데이터 + 유사도)"""
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"text": doc, "similarity": 1 - dist, **meta}
        for doc, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]
