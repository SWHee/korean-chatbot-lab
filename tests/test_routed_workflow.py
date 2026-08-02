"""질문 분석부터 route별 최종 답변까지의 Workflow 검증"""

import pytest

from chatbot import graph as graph_module
from chatbot.rag import INSUFFICIENT_EVIDENCE_MESSAGE


def _deposit_result() -> dict:
    """Routed Workflow용 Finlife 정기예금 응답"""
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


class FakeAnalysisGenerator:
    """고정된 질문 분석 결과를 반환하는 생성기 대역"""

    def __init__(self, analysis: dict) -> None:
        self.analysis = analysis

    def generate_structured(self, *, messages, response_model):
        return response_model.model_validate(self.analysis)


def _product_filters(*, term_months: int = 12) -> dict:
    return {
        "product_type": "deposit",
        "term_months": term_months,
        "sort_by": "base_interest_rate",
        "limit": 3,
    }


def _analysis(*, route: str, **overrides) -> dict:
    result = {
        "route": route,
        "law_question": None,
        "product_filters": None,
        "missing_fields": [],
        "clarifying_question": None,
    }
    result.update(overrides)
    return result


def _create_graph(analysis: dict):
    return graph_module.create_routed_workflow_graph(
        generator=FakeAnalysisGenerator(analysis),
        encoder=object(),
        collection=object(),
    )


def test_routed_workflow_returns_law_answer(monkeypatch) -> None:
    """law route의 검색 결과를 기존 법령 RAG 답변으로 연결"""
    articles = [{"law_name": "예금자보호법", "article_no": "제32조"}]
    monkeypatch.setattr(
        graph_module,
        "retrieve_articles",
        lambda **kwargs: articles,
    )
    monkeypatch.setattr(
        graph_module,
        "answer_question",
        lambda **kwargs: "예금자보호 한도에 관한 법령 안내입니다.",
    )

    graph = _create_graph(
        _analysis(
            route="law",
            law_question="예금자보호 한도를 알려주세요.",
        )
    )
    result = graph.invoke({"question": "예금자보호 한도를 알려주세요."})

    assert result["route"] == "law"
    assert result["law_status"] == "ok"
    assert result["answer"] == "예금자보호 한도에 관한 법령 안내입니다."


def test_routed_workflow_renders_ranked_product_answer(monkeypatch) -> None:
    """product route의 정렬된 후보를 일정한 형식으로 표시"""
    monkeypatch.setattr(
        graph_module,
        "fetch_deposit_products",
        _deposit_result,
    )
    graph = _create_graph(
        _analysis(
            route="product",
            product_filters=_product_filters(),
        )
    )

    result = graph.invoke({"question": "12개월 정기예금을 비교해 주세요."})

    assert result["product_status"] == "ok"
    assert result["answer"] == (
        "12개월 정기예금을 기본금리 기준으로 비교했어요.\n\n"
        "1. 테스트은행 · 테스트예금\n"
        "   기본금리 3.10% · 최고금리 3.50% · 공시월 2026년 07월\n\n"
        "공시 정보는 조회 시점 기준이며, 가입 전 금융회사의 "
        "최신 상품설명서를 확인해 주세요."
    )


def test_routed_workflow_combines_mixed_answer_without_second_generation(
    monkeypatch,
) -> None:
    """mixed route의 법령·상품 완성 답변 결합"""
    monkeypatch.setattr(
        graph_module,
        "retrieve_articles",
        lambda **kwargs: [{"law_name": "예금자보호법", "article_no": "제32조"}],
    )
    monkeypatch.setattr(
        graph_module,
        "answer_question",
        lambda **kwargs: "예금자보호 한도에 관한 법령 안내입니다.",
    )
    monkeypatch.setattr(
        graph_module,
        "fetch_deposit_products",
        _deposit_result,
    )
    graph = _create_graph(
        _analysis(
            route="mixed",
            law_question="예금자보호 한도를 알려주세요.",
            product_filters=_product_filters(),
        )
    )

    result = graph.invoke(
        {"question": "12개월 정기예금과 예금자보호 한도를 알려주세요."}
    )

    assert result["law_status"] == "ok"
    assert result["product_status"] == "ok"
    assert result["answer"].startswith(
        "법령 안내\n예금자보호 한도에 관한 법령 안내입니다.\n\n상품 비교\n"
    )
    assert "테스트은행 · 테스트예금" in result["answer"]


@pytest.mark.parametrize(
    ("analysis", "expected_answer"),
    [
        (
            _analysis(
                route="clarify",
                product_filters=_product_filters(term_months=12)
                | {"product_type": None},
                missing_fields=["product_type"],
                clarifying_question="정기예금과 적금 중 어떤 상품을 찾으시나요?",
            ),
            "정기예금과 적금 중 어떤 상품을 찾으시나요?",
        ),
        (
            _analysis(route="out_of_scope"),
            (
                "현재는 예금·적금 상품 비교와 금융소비자보호 법령 안내를 "
                "도와드릴 수 있어요.\n"
                "예: ‘12개월 정기예금을 비교해 주세요’ 또는 "
                "‘예금자보호 한도를 알려주세요’"
            ),
        ),
    ],
)
def test_routed_workflow_returns_non_search_answers(
    analysis: dict,
    expected_answer: str,
) -> None:
    """clarify와 out-of-scope route의 안내 답변"""
    graph = _create_graph(analysis)

    result = graph.invoke({"question": "질문"})

    assert result["answer"] == expected_answer


def test_routed_workflow_marks_insufficient_law_evidence(monkeypatch) -> None:
    """법령 RAG 근거 부족 상태와 안내 문구 유지"""
    monkeypatch.setattr(
        graph_module,
        "retrieve_articles",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        graph_module,
        "answer_question",
        lambda **kwargs: INSUFFICIENT_EVIDENCE_MESSAGE,
    )
    graph = _create_graph(
        _analysis(
            route="law",
            law_question="개별 상품도 보호되나요?",
        )
    )

    result = graph.invoke({"question": "개별 상품도 보호되나요?"})

    assert result["law_status"] == "insufficient_evidence"
    assert result["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE


def test_routed_workflow_explains_missing_product_match(monkeypatch) -> None:
    """상품 후보가 없을 때 조건 변경 방법 안내"""
    monkeypatch.setattr(
        graph_module,
        "fetch_deposit_products",
        _deposit_result,
    )
    graph = _create_graph(
        _analysis(
            route="product",
            product_filters=_product_filters(term_months=24),
        )
    )

    result = graph.invoke({"question": "24개월 정기예금을 비교해 주세요."})

    assert result["product_status"] == "no_match"
    assert result["answer"] == (
        "24개월 정기예금 중 비교할 수 있는 상품을 찾지 못했어요.\n"
        "기간이나 비교 기준을 바꿔 다시 확인해 주세요."
    )


def test_routed_workflow_keeps_law_answer_when_product_branch_fails(
    monkeypatch,
) -> None:
    """mixed 상품 실패 시 법령 답변과 오류 안내를 함께 반환"""
    monkeypatch.setattr(
        graph_module,
        "retrieve_articles",
        lambda **kwargs: [{"law_name": "예금자보호법", "article_no": "제32조"}],
    )
    monkeypatch.setattr(
        graph_module,
        "answer_question",
        lambda **kwargs: "예금자보호 한도에 관한 법령 안내입니다.",
    )

    def raise_finlife_error() -> dict:
        raise RuntimeError("Finlife API 오류")

    monkeypatch.setattr(
        graph_module,
        "fetch_deposit_products",
        raise_finlife_error,
    )
    graph = _create_graph(
        _analysis(
            route="mixed",
            law_question="예금자보호 한도를 알려주세요.",
            product_filters=_product_filters(),
        )
    )

    result = graph.invoke(
        {"question": "12개월 정기예금과 예금자보호 한도를 알려주세요."}
    )

    assert result["law_status"] == "ok"
    assert result["product_status"] == "error"
    assert "예금자보호 한도에 관한 법령 안내입니다." in result["answer"]
    assert "금융상품 공시 정보를 불러오지 못했어요." in result["answer"]
