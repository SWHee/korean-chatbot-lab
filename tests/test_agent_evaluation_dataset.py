"""Agent 개발 Dataset 계약 검증"""

from collections import Counter

from chatbot.evaluation.agent_dataset import (
    AGENT_DATASET_VERSION,
    FINLIFE_FIXTURE_VERSION,
    load_agent_evaluation_cases,
    load_finlife_fixture,
)


def test_agent_dataset_has_fixed_32_case_distribution() -> None:
    """법령·상품·혼합·경계 경로를 같은 수로 구성"""
    cases = load_agent_evaluation_cases()

    assert len(cases) == 32
    assert Counter(case.category for case in cases) == {
        "law": 8,
        "product": 8,
        "mixed": 8,
        "boundary": 8,
    }
    assert {case.dataset_version for case in cases} == {AGENT_DATASET_VERSION}


def test_agent_dataset_keeps_eight_two_turn_trajectories() -> None:
    """추가 질문과 조건 병합을 별도 실행 경로로 기록"""
    cases = load_agent_evaluation_cases()
    multi_turn_cases = [case for case in cases if len(case.turns) == 2]

    assert len(multi_turn_cases) == 8
    assert all(case.turns[0].expected_route == "clarify" for case in multi_turn_cases)
    assert all(case.turns[1].expected_route == "ready" for case in multi_turn_cases)


def test_product_tool_cases_use_fixed_finlife_fixture() -> None:
    """상품 후보와 금리 비교를 live API 변화에서 분리"""
    cases = load_agent_evaluation_cases()
    product_tool_cases = [
        case
        for case in cases
        if any(
            tool.name == "search_financial_products"
            for turn in case.turns
            for tool in turn.expected_tools
        )
    ]

    assert product_tool_cases
    assert all(
        case.finlife_fixture_version == FINLIFE_FIXTURE_VERSION
        for case in product_tool_cases
    )


def test_finlife_fixture_contains_products_and_rate_options() -> None:
    """상품 Tool 평가에 필요한 원본 상품·옵션 배열 유지"""
    fixture = load_finlife_fixture()

    assert fixture["baseList"]
    assert fixture["optionList"]
