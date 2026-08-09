import uuid

import chromadb

from chatbot.law.vectorstore import resolve_index_dir, search


def make_collection():
    """인메모리 코사인 컬렉션에 방향이 다른 벡터 2개 저장"""
    client = chromadb.EphemeralClient()  # 프로세스 내 상태 공유 → 고유 이름 필요
    collection = client.create_collection(
        f"test-{uuid.uuid4().hex[:8]}", metadata={"hnsw:space": "cosine"}
    )
    collection.add(
        ids=["a", "b"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=["문서A", "문서B"],
        metadatas=[
            {"law_name": "예금자보호법", "article_no": "제1조"},
            {"law_name": "예금자보호법", "article_no": "제2조"},
        ],
    )
    return collection


def test_search_returns_nearest_with_metadata() -> None:
    """가까운 벡터의 본문·메타데이터·유사도 반환"""
    result = search(make_collection(), [1.0, 0.05], top_k=1)
    assert len(result) == 1
    assert result[0]["text"] == "문서A"
    assert result[0]["article_no"] == "제1조"
    assert result[0]["similarity"] > 0.9


def test_search_top_k_order() -> None:
    """top_k 개수와 유사도 내림차순 보장"""
    result = search(make_collection(), [0.3, 1.0], top_k=2)
    assert [r["article_no"] for r in result] == ["제2조", "제1조"]
    assert result[0]["similarity"] >= result[1]["similarity"]


def test_resolve_index_dir_uses_environment(
    monkeypatch, tmp_path
) -> None:
    """컨테이너에서 지정한 인덱스 경로 우선"""
    index_dir = tmp_path / "chroma"
    monkeypatch.setenv("CHATBOT_INDEX_DIR", str(index_dir))

    assert resolve_index_dir() == index_dir
