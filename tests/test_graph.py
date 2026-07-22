"""법령 RAG StateGraph 실행 흐름 검증"""

from chatbot import graph as graph_module


def test_rag_graph_retrieves_articles_before_generating_answer(monkeypatch) -> None:
    question = "은행이 파산하면 예금은 얼마까지 보호받나요?"
    articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "text": "보험금의 한도는 1억원으로 한다.",
        }
    ]
    calls = []
    expected_generator = object()
    expected_encoder = object()
    expected_collection = object()
    expected_question = question
    expected_articles = articles

    def fake_retrieve_articles(
        *, encoder, collection, question: str, top_k: int
    ) -> list[dict]:
        calls.append("retrieve")
        assert encoder is expected_encoder
        assert collection is expected_collection
        assert question == expected_question
        assert top_k == graph_module.DEFAULT_TOP_K
        return articles

    def fake_answer_question(
        *, generator, question: str, articles: list[dict]
    ) -> str:
        calls.append("generate")
        assert generator is expected_generator
        assert question == expected_question
        assert articles == expected_articles
        return "예금자 1인당 1억원까지 보호됩니다."

    monkeypatch.setattr(graph_module, "retrieve_articles", fake_retrieve_articles)
    monkeypatch.setattr(graph_module, "answer_question", fake_answer_question)

    graph = graph_module.create_rag_graph(
        generator=expected_generator,
        encoder=expected_encoder,
        collection=expected_collection,
    )
    result = graph.invoke({"question": question})

    assert calls == ["retrieve", "generate"]
    assert result == {
        "question": question,
        "articles": articles,
        "answer": "예금자 1인당 1억원까지 보호됩니다.",
    }
