"""법령 retriever 단위 테스트"""

import torch
import pytest

import chatbot.retriever as retriever_module
from chatbot.retriever import embed_query


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

    def fake_retrieve_chunks(encoder, collection, question, top_k):
        calls["top_k"] = top_k
        return chunks

    monkeypatch.setattr(retriever_module, "retrieve_chunks", fake_retrieve_chunks)

    results = retriever_module.retrieve_articles(
        object(), object(), "보호 한도는 얼마인가요?", top_k=2, candidate_k=3
    )

    assert calls["top_k"] == 3
    assert [r["article_no"] for r in results] == ["제18조", "제32조"]
