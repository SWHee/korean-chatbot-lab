"""법령 RAG StateGraph 실행 흐름 검증"""

from chatbot import graph as graph_module


def _deposit_result() -> dict:
    """Product Graph 테스트용 Finlife 원본 응답"""
    return {
        "baseList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "DEPOSIT-001",
                "kor_co_nm": "테스트은행",
                "fin_prdt_nm": "테스트예금",
            }
        ],
        "optionList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "DEPOSIT-001",
                "save_trm": "12",
                "intr_rate": 3.1,
                "intr_rate2": 3.5,
            }
        ],
    }


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


def test_rag_graph_streams_answer_chunks(monkeypatch) -> None:
    """생성 Node의 답변 조각을 Graph custom stream으로 전달"""
    question = "예금은 얼마까지 보호되나요?"
    articles = [{"article_no": "제18조"}]

    monkeypatch.setattr(
        graph_module,
        "retrieve_articles",
        lambda **kwargs: articles,
    )
    monkeypatch.setattr(
        graph_module,
        "stream_answer_question",
        lambda **kwargs: iter(["예금은 ", "1억원까지 보호됩니다."]),
    )

    graph = graph_module.create_rag_graph(
        generator=object(),
        encoder=object(),
        collection=object(),
    )
    chunks = list(
        graph.stream(
            {"question": question, "streaming": True},
            stream_mode="custom",
        )
    )

    assert chunks == ["예금은 ", "1억원까지 보호됩니다."]


def test_product_graph_returns_ranked_products(monkeypatch) -> None:
    """구조화 조건으로 정기예금 후보와 성공 상태 반환"""
    monkeypatch.setattr(
        graph_module,
        "fetch_deposit_products",
        _deposit_result,
    )

    graph = graph_module.create_product_graph()
    result = graph.invoke(
        {
            "term_months": 12,
            "sort_by": "base_interest_rate",
            "limit": 3,
        }
    )

    assert result["product_status"] == "ok"
    assert [product.product_code for product in result["products"]] == [
        "DEPOSIT-001"
    ]


def test_product_graph_marks_no_match(monkeypatch) -> None:
    """요청 기간에 맞는 후보가 없으면 no_match 상태 반환"""
    monkeypatch.setattr(
        graph_module,
        "fetch_deposit_products",
        _deposit_result,
    )

    graph = graph_module.create_product_graph()
    result = graph.invoke(
        {
            "term_months": 24,
            "sort_by": "base_interest_rate",
            "limit": 3,
        }
    )

    assert result["products"] == []
    assert result["product_status"] == "no_match"


def test_product_graph_marks_expected_api_error(monkeypatch) -> None:
    """Finlife 본문 오류를 상품 조회 오류 상태로 변환"""
    def raise_finlife_error() -> dict:
        raise RuntimeError("Finlife API error 101: 잘못된 요청")

    monkeypatch.setattr(
        graph_module,
        "fetch_deposit_products",
        raise_finlife_error,
    )

    graph = graph_module.create_product_graph()
    result = graph.invoke(
        {
            "term_months": 12,
            "sort_by": "base_interest_rate",
            "limit": 3,
        }
    )

    assert result["products"] == []
    assert result["product_status"] == "error"
