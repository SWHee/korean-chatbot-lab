"""법령 retriever 단위 테스트"""

import torch
import pytest

import chatbot.rag.retrieval as retriever_module
from chatbot.rag.retrieval import embed_query


class FakeEncoder:
    """모델 적재 없는 고정 질문 벡터"""

    def encode(self, texts, **kwargs):
        return torch.tensor([[0.1, 0.2, 0.3]])


class FakeCollection:
    """Chroma 적재 없는 고정 검색 결과"""

    def __init__(self) -> None:
        self.query_embeddings = None
        self.n_results = None

    def query(self, query_embeddings, n_results, include):
        self.query_embeddings = query_embeddings
        self.n_results = n_results
        return {
            "documents": [["예금자보호 한도는 1억원"]],
            "metadatas": [[{"law_name": "예금자보호법 시행령", "article_no": "제18조"}]],
            "distances": [[0.2]],
        }


def test_embed_query_returns_one_vector() -> None:
    """질문 하나를 벡터 하나로 변환"""
    vector = embed_query(FakeEncoder(), "예금은 얼마까지 보호되나요?")

    assert vector == pytest.approx([0.1, 0.2, 0.3])


def test_retrieve_chunks_searches_with_query_vector() -> None:
    """질문 벡터로 지정한 개수의 청크 검색"""
    collection = FakeCollection()

    results = retriever_module.retrieve_chunks(
        FakeEncoder(), collection, "예금은 얼마까지 보호되나요?", top_k=1
    )

    assert collection.query_embeddings[0] == pytest.approx([0.1, 0.2, 0.3])
    assert collection.n_results == 1
    assert results[0]["article_no"] == "제18조"


def test_deduplicate_articles_keeps_best_chunk() -> None:
    """같은 조문에서 가장 높은 유사도의 청크만 유지"""
    chunks = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "chunk_index": 0,
            "similarity": 0.9,
        },
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "chunk_index": 1,
            "similarity": 0.8,
        },
        {
            "law_name": "예금자보호법",
            "article_no": "제32조",
            "chunk_index": 0,
            "similarity": 0.7,
        },
    ]

    results = retriever_module.deduplicate_articles(chunks, top_k=2)

    assert [(r["law_name"], r["article_no"]) for r in results] == [
        ("예금자보호법 시행령", "제18조"),
        ("예금자보호법", "제32조"),
    ]
    assert results[0]["chunk_index"] == 0


def test_retrieve_articles_deduplicates_candidate_chunks(monkeypatch) -> None:
    """후보 청크를 넉넉히 검색한 뒤 상위 조문으로 축소"""
    calls = {}
    chunks = [
        {"law_name": "시행령", "article_no": "제18조", "similarity": 0.9},
        {"law_name": "시행령", "article_no": "제18조", "similarity": 0.8},
        {"law_name": "법률", "article_no": "제32조", "similarity": 0.7},
    ]

    def fake_retrieve_hybrid_chunks(encoder, collection, question, top_k):
        calls["top_k"] = top_k
        return chunks

    monkeypatch.setattr(
        retriever_module, "retrieve_hybrid_chunks", fake_retrieve_hybrid_chunks
    )

    results = retriever_module.retrieve_articles(
        object(), object(), "보호 한도는 얼마인가요?", top_k=2, candidate_k=3
    )

    assert calls["top_k"] == 3
    assert [r["article_no"] for r in results] == ["제18조", "제32조"]


def test_retrieve_hybrid_chunks_promotes_exact_keyword_match(monkeypatch) -> None:
    """의미 검색과 키워드 검색 모두 높은 조문 우선"""
    dense_chunks = [
        {
            "law_name": "금융소비자보호법",
            "article_no": "제1조",
            "chunk_index": 0,
            "text": "금융소비자 보호의 목적",
            "similarity": 0.9,
        },
        {
            "law_name": "예금자보호법",
            "article_no": "제18조",
            "chunk_index": 0,
            "text": "예금자보호 한도",
            "similarity": 0.8,
        },
    ]
    keyword_chunks = [dense_chunks[1]]

    monkeypatch.setattr(
        retriever_module,
        "retrieve_chunks",
        lambda encoder, collection, question, top_k: dense_chunks,
    )
    monkeypatch.setattr(
        retriever_module,
        "retrieve_keyword_chunks",
        lambda collection, question, top_k: keyword_chunks,
    )

    results = retriever_module.retrieve_hybrid_chunks(
        object(), object(), "예금자보호 한도", top_k=2
    )

    assert [chunk["article_no"] for chunk in results] == ["제18조", "제1조"]


def test_retrieve_keyword_chunks_ranks_exact_law_term_first() -> None:
    """BM25 검색에서 질문의 법령명이 있는 청크 우선"""

    class KeywordCollection:
        """고정 법령 청크 반환"""

        def get(self, include):
            return {
                "documents": ["금융소비자의 권리", "예금자보호법 보호 한도"],
                "metadatas": [
                    {
                        "law_name": "금융소비자보호법",
                        "article_no": "제1조",
                        "chunk_index": 0,
                    },
                    {
                        "law_name": "예금자보호법",
                        "article_no": "제18조",
                        "chunk_index": 0,
                    },
                ],
            }

    results = retriever_module.retrieve_keyword_chunks(
        KeywordCollection(), "예금자보호법 한도"
    )

    assert [chunk["article_no"] for chunk in results] == ["제18조"]


def test_tokenize_for_bm25_extracts_korean_content_words() -> None:
    """활용형 질문과 법령 문구가 공유하는 한국어 조각 생성"""
    question_tokens = retriever_module.tokenize_for_bm25(
        "은행이 파산하면 내 예금은 얼마까지 보호받나요?"
    )
    law_tokens = retriever_module.tokenize_for_bm25(
        "은행 파산 시 예금 보호 한도"
    )

    assert {"은행", "파산", "예금", "보호"} <= (
        set(question_tokens) & set(law_tokens)
    )


def test_retrieve_keyword_chunks_ignores_one_weak_shared_token() -> None:
    """핵심어 하나만 겹치는 약한 BM25 결과 제외"""

    class WeakMatchCollection:
        """일반 단어 하나만 겹치는 법령 청크 반환"""

        def get(self, include):
            return {
                "documents": ["예금보험기금 내 계정의 이자 감면"],
                "metadatas": [
                    {
                        "law_name": "예금자보호법 시행령",
                        "article_no": "제14조의2",
                        "chunk_index": 0,
                    }
                ],
            }

    results = retriever_module.retrieve_keyword_chunks(
        WeakMatchCollection(),
        "은행이 파산하면 내 예금은 얼마까지 보호받나요?",
    )

    assert results == []


def test_reciprocal_rank_fusion_preserves_dense_similarity() -> None:
    """동일 청크 결합 시 dense 검색 메타데이터 유지"""
    dense_chunk = {
        "law_name": "예금자보호법 시행령",
        "article_no": "제18조",
        "chunk_index": 2,
        "text": "보험금 지급한도는 1억원",
        "similarity": 0.82,
    }
    keyword_chunk = {
        key: value for key, value in dense_chunk.items() if key != "similarity"
    }

    results = retriever_module.reciprocal_rank_fusion(
        [dense_chunk], [keyword_chunk]
    )

    assert results[0]["similarity"] == 0.82


def test_reciprocal_rank_fusion_keeps_keyword_as_secondary_signal() -> None:
    """BM25 단독 후보보다 dense 상위 후보 우선"""
    dense_chunks = [
        {
            "law_name": "나법",
            "article_no": "제1조",
            "chunk_index": 0,
            "text": "dense 1위",
            "similarity": 0.9,
        },
        {
            "law_name": "다법",
            "article_no": "제2조",
            "chunk_index": 0,
            "text": "dense 2위",
            "similarity": 0.8,
        },
    ]
    keyword_chunks = [
        {
            "law_name": "가법",
            "article_no": "제3조",
            "chunk_index": 0,
            "text": "BM25 단독 1위",
        }
    ]

    results = retriever_module.reciprocal_rank_fusion(
        dense_chunks,
        keyword_chunks,
    )

    assert [chunk["article_no"] for chunk in results[:2]] == ["제1조", "제2조"]
