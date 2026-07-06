"""법령 청크 벡터스토어 접근 (ADR 0006: Chroma)"""

from pathlib import Path

import chromadb

INDEX_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "index" / "chroma"
COLLECTION_NAME = "statutes"


def open_collection(index_dir: str | Path = INDEX_DIR):
    """persist된 인덱스 컬렉션 열기"""
    client = chromadb.PersistentClient(path=str(index_dir))
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
