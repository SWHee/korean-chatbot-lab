"""법령 질문의 의미·키워드 검색과 조문 단위 정리"""

import re
import unicodedata

from rank_bm25 import BM25Okapi

from chatbot.embedding import embed_texts
from chatbot.vectorstore import search

DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 50
RRF_K = 60
BM25_RRF_WEIGHT = 0.1
BM25_NGRAM_SIZE = 2
MIN_BM25_SHARED_TOKENS = 2
BM25_WORD_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+")


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


def tokenize_for_bm25(text: str) -> list[str]:
    """조사·어미 변화에 겹치는 한국어 2-gram 토큰"""
    normalized_text = unicodedata.normalize("NFC", text).lower()
    return [
        word[index : index + BM25_NGRAM_SIZE]
        for word in BM25_WORD_PATTERN.findall(normalized_text)
        if len(word) >= BM25_NGRAM_SIZE
        for index in range(len(word) - BM25_NGRAM_SIZE + 1)
    ]


def retrieve_keyword_chunks(
    collection,
    question: str,
    top_k: int = DEFAULT_CANDIDATE_K,
) -> list[dict]:
    """BM25 점수가 있는 법령 청크 목록"""
    result = collection.get(include=["documents", "metadatas"])
    chunks = [
        {"text": document, **metadata}
        for document, metadata in zip(result["documents"], result["metadatas"])
    ]
    if not chunks:
        return []

    tokenized_chunks = [tokenize_for_bm25(chunk["text"]) for chunk in chunks]
    question_tokens = tokenize_for_bm25(question)
    bm25 = BM25Okapi(tokenized_chunks)
    scores = bm25.get_scores(question_tokens)
    question_token_set = set(question_tokens)
    ranked_indices = sorted(
        (
            index
            for index, tokens in enumerate(tokenized_chunks)
            if len(question_token_set & set(tokens)) >= MIN_BM25_SHARED_TOKENS
        ),
        key=lambda index: (
            -scores[index],
            -len(question_token_set & set(tokenized_chunks[index])),
            index,
        ),
    )
    return [
        chunks[index] | {"bm25_score": float(scores[index])}
        for index in ranked_indices[:top_k]
    ]


def _chunk_key(chunk: dict) -> tuple[str, str, int]:
    """RRF 결합을 위한 법령 청크 식별값"""
    return (chunk["law_name"], chunk["article_no"], chunk["chunk_index"])


def reciprocal_rank_fusion(
    dense_chunks: list[dict],
    keyword_chunks: list[dict],
) -> list[dict]:
    """dense 우선 가중치를 적용한 RRF 결합 결과"""
    scores: dict[tuple[str, str, int], float] = {}
    chunks_by_key: dict[tuple[str, str, int], dict] = {}

    weighted_rankings = (
        (1.0, dense_chunks),
        (BM25_RRF_WEIGHT, keyword_chunks),
    )
    for weight, ranked_list in weighted_rankings:
        for rank, chunk in enumerate(ranked_list, start=1):
            key = _chunk_key(chunk)
            scores[key] = scores.get(key, 0.0) + weight / (RRF_K + rank)
            chunks_by_key[key] = {**chunk, **chunks_by_key.get(key, {})}

    ranked_keys = sorted(scores, key=lambda key: (-scores[key], key))
    fused_chunks = []
    for key in ranked_keys:
        chunk = chunks_by_key[key] | {"rrf_score": scores[key]}
        chunk.setdefault("similarity", 0.0)
        fused_chunks.append(chunk)
    return fused_chunks


def retrieve_hybrid_chunks(
    encoder,
    collection,
    question: str,
    top_k: int = DEFAULT_CANDIDATE_K,
) -> list[dict]:
    """의미 검색과 BM25 키워드 검색의 RRF 결합"""
    dense_chunks = retrieve_chunks(encoder, collection, question, top_k=top_k)
    keyword_chunks = retrieve_keyword_chunks(collection, question, top_k=top_k)
    return reciprocal_rank_fusion(dense_chunks, keyword_chunks)


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
    """하이브리드 후보 검색과 조문 단위 중복 제거"""
    chunks = retrieve_hybrid_chunks(encoder, collection, question, top_k=candidate_k)
    return deduplicate_articles(chunks, top_k=top_k)
