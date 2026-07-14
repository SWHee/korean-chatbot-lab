"""법령 질문의 임베딩과 Chroma 검색 연결"""

from chatbot.embedding import embed_texts
from chatbot.vectorstore import search

DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 50


def embed_query(encoder, question: str) -> list[float]:
    """질문 하나의 정규화된 임베딩 벡터"""
    return embed_texts(encoder, [question])[0]


def retrieve_chunks(
    encoder,
    collection,
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """질문과 가까운 법령 청크 목록"""
    query_embedding = embed_query(encoder, question)
    return search(collection, query_embedding, top_k=top_k)


def deduplicate_articles(
    chunks: list[dict],
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """법령명과 조문번호가 겹치지 않는 상위 청크 목록"""
    selected = []
    seen = set()

    for chunk in chunks:
        key = (chunk["law_name"], chunk["article_no"])
        if key in seen:
            continue

        seen.add(key)
        selected.append(chunk)

        if len(selected) == top_k:
            break

    return selected


def retrieve_articles(
    encoder,
    collection,
    question: str,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = DEFAULT_CANDIDATE_K,
) -> list[dict]:
    """후보 청크 검색과 조문 단위 중복 제거"""
    chunks = retrieve_chunks(encoder, collection, question, top_k=candidate_k)
    return deduplicate_articles(chunks, top_k=top_k)
