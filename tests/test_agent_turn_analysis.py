"""현재 대화와 저장된 조건을 함께 분석하는 계약 검증"""

from chatbot.agent.turn_analysis import (
    ProductFilters,
    TurnIntent,
    create_turn_analyzer,
)


class FakeGenerator:
    """구조화 응답을 기록하는 생성기 대역"""

    def __init__(self) -> None:
        self.messages = None

    def generate_structured(self, *, messages, response_model):
        self.messages = messages
        assert response_model is TurnIntent
        return TurnIntent(intent="product", term_months=12)


def test_turn_analyzer_includes_saved_preferences_in_structured_request() -> None:
    """후속 답변 분석 시 같은 thread의 확정 조건 전달"""
    generator = FakeGenerator()
    analyze_turn = create_turn_analyzer(generator=generator)

    result = analyze_turn(
        message="12개월이요.",
        previous_preferences={"product_type": "deposit", "term_months": None},
    )

    assert result == TurnIntent(intent="product", term_months=12)
    assert "deposit" in generator.messages[1]["content"]
    assert "12개월이요." in generator.messages[1]["content"]


def test_product_filters_reports_missing_required_preferences() -> None:
    """Agent 상품 조회 전 부족한 조건 확인"""
    filters = ProductFilters(product_type="saving")

    assert filters.missing_required_fields() == ["term_months"]
