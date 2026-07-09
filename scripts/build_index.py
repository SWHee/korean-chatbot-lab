"""전체 인덱싱 1회 배치: 조문 파싱 → 청킹 → KURE-v1 임베딩 → Chroma persist.

사용법: uv run python scripts/build_index.py
재실행 시 기존 컬렉션을 지우고 새로 만듭니다.
데이터 공개 기준은 data/laws/README.md 참고.

문서를 벡터스토어에 넣는 일반적인 ingest.py와 같은 역할입니다.
이 프로젝트에서는 증분 추가보다 전체 법령 snapshot 재생성을 기준으로 합니다.
"""

from pathlib import Path

import chromadb

from chatbot.chunking import chunk_articles
from chatbot.embedding import load_encoder, embed_texts
from chatbot.statutes import parse_law
from chatbot.vectorstore import COLLECTION_NAME, INDEX_DIR

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "laws"


def main() -> None:
    articles = []
    for f in sorted(DATA_DIR.glob("*.xml")):
        articles += parse_law(f)
    chunks = chunk_articles(articles)
    print(f"조문 {len(articles)}개 → 청크 {len(chunks)}개", flush=True)

    encoder = load_encoder()
    vectors = embed_texts(encoder, [c.text for c in chunks])

    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    if any(c.name == COLLECTION_NAME for c in client.list_collections()):
        client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    collection.add(
        ids=[f"{c.law_name}|{c.article_no}|{c.chunk_index}" for c in chunks],
        embeddings=vectors,
        documents=[c.text for c in chunks],
        metadatas=[
            {
                "law_name": c.law_name,
                "article_no": c.article_no,
                "title": c.title,
                "effective_date": c.effective_date,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ],
    )
    print(f"인덱싱 완료: {collection.count()}개 청크 → {INDEX_DIR}", flush=True)


if __name__ == "__main__":
    main()
