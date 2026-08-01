"""법령 RAG StateGraph 실행 흐름 검증"""

import pytest

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


def test_fixed_route_graph_runs_only_selected_node() -> None:
    """route 값에 따라 법령 또는 상품 Node 한 곳만 실행"""
    graph = graph_module.create_fixed_route_graph()

    law_result = graph.invoke({"route": "law"})
    product_result = graph.invoke({"route": "product"})

    assert law_result == {
        "route": "law",
        "executed_node": "law_node",
    }
    assert product_result == {
        "route": "product",
        "executed_node": "product_node",
    }


def test_fixed_route_graph_mermaid_contains_both_route_nodes() -> None:
    """조건부 Edge의 law·product Node 노출"""
    graph = graph_module.create_fixed_route_graph()

    mermaid_text = graph.get_graph().draw_mermaid()

    assert "law_node" in mermaid_text
    assert "product_node" in mermaid_text


class FakeQuestionAnalysisGenerator:
    """구조화 질문 분석 결과를 반환하는 생성기 대역"""

    def __init__(self, response: dict) -> None:
        self.response = response
        self.requests = []

    def generate_structured(self, *, messages, response_model):
        self.requests.append(
            {
                "messages": messages,
                "response_model": response_model,
            }
        )
        return response_model.model_validate(self.response)


def test_question_analysis_graph_returns_law_route() -> None:
    """법령 질문을 law route와 법령 검색 질문으로 변환"""
    generator = FakeQuestionAnalysisGenerator(
        {
            "route": "law",
            "law_question": "예금자보호 한도는 얼마인가요?",
            "product_filters": None,
            "missing_fields": [],
            "clarifying_question": None,
        }
    )

    graph = graph_module.create_question_analysis_graph(generator)
    result = graph.invoke({"question": "예금자보호 한도는 얼마인가요?"})

    assert result["route"] == "law"
    assert result["law_question"] == "예금자보호 한도는 얼마인가요?"
    assert result["product_filters"] is None
    assert generator.requests[0]["response_model"] is graph_module.QuestionAnalysis


def test_question_analysis_graph_returns_product_route() -> None:
    """조건이 충분한 정기예금 질문을 상품 조회 조건으로 변환"""
    generator = FakeQuestionAnalysisGenerator(
        {
            "route": "product",
            "law_question": None,
            "product_filters": {
                "product_type": "deposit",
                "term_months": 12,
                "sort_by": "base_interest_rate",
                "limit": 3,
            },
            "missing_fields": [],
            "clarifying_question": None,
        }
    )

    graph = graph_module.create_question_analysis_graph(generator)
    result = graph.invoke({"question": "12개월 정기예금을 비교해 주세요."})

    assert result["route"] == "product"
    assert result["product_filters"] == {
        "product_type": "deposit",
        "term_months": 12,
        "sort_by": "base_interest_rate",
        "limit": 3,
    }


def test_question_analysis_graph_returns_mixed_route() -> None:
    """상품 비교와 법령 설명이 함께 있으면 mixed route 반환"""
    generator = FakeQuestionAnalysisGenerator(
        {
            "route": "mixed",
            "law_question": "예금자보호 한도를 알려주세요.",
            "product_filters": {
                "product_type": "deposit",
                "term_months": 12,
                "sort_by": "base_interest_rate",
                "limit": 3,
            },
            "missing_fields": [],
            "clarifying_question": None,
        }
    )

    graph = graph_module.create_question_analysis_graph(generator)
    result = graph.invoke(
        {
            "question": "12개월 정기예금과 예금자보호 한도를 알려주세요.",
        }
    )

    assert result["route"] == "mixed"
    assert result["law_question"] == "예금자보호 한도를 알려주세요."
    assert result["product_filters"]["term_months"] == 12


def test_question_analysis_graph_returns_clarify_route() -> None:
    """상품 의도는 있으나 조건이 부족하면 추가 질문 반환"""
    generator = FakeQuestionAnalysisGenerator(
        {
            "route": "clarify",
            "law_question": None,
            "product_filters": {
                "product_type": None,
                "term_months": None,
                "sort_by": "base_interest_rate",
                "limit": 3,
            },
            "missing_fields": ["product_type", "term_months"],
            "clarifying_question": "예금과 적금 중 무엇을 찾으시고, 희망 기간은 몇 개월인가요?",
        }
    )

    graph = graph_module.create_question_analysis_graph(generator)
    result = graph.invoke({"question": "금융상품을 추천해 주세요."})

    assert result["route"] == "clarify"
    assert result["missing_fields"] == ["product_type", "term_months"]
    assert "예금과 적금" in result["clarifying_question"]


def test_question_analysis_graph_returns_out_of_scope_route() -> None:
    """예·적금과 법령 범위 밖 질문을 out_of_scope로 변환"""
    generator = FakeQuestionAnalysisGenerator(
        {
            "route": "out_of_scope",
            "law_question": None,
            "product_filters": None,
            "missing_fields": [],
            "clarifying_question": None,
        }
    )

    graph = graph_module.create_question_analysis_graph(generator)
    result = graph.invoke({"question": "오늘 서울 날씨를 알려주세요."})

    assert result["route"] == "out_of_scope"
    assert result["product_filters"] is None


def test_question_analysis_rejects_incomplete_product_route() -> None:
    """상품 route에는 상품 종류와 기간이 모두 필요"""
    with pytest.raises(ValueError, match="product route requires"):
        graph_module.QuestionAnalysis.model_validate(
            {
                "route": "product",
                "law_question": None,
                "product_filters": {
                    "product_type": "deposit",
                    "term_months": None,
                    "sort_by": "base_interest_rate",
                    "limit": 3,
                },
                "missing_fields": [],
                "clarifying_question": None,
            }
        )
