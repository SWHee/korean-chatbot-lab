"""Agent Tool 입력 계약 검증"""

import pytest
from pydantic import ValidationError

from chatbot.agent import tools as tool_module
from chatbot.agent.tools import SearchFinancialProductsInput


def test_product_tool_schema_keeps_positive_validation_outside_api_schema() -> None:
    """Anthropic strict 호환 schema와 로컬 양수 검증 유지"""
    api_schema = SearchFinancialProductsInput.model_json_schema()

    assert "minimum" not in api_schema["properties"]["term_months"]
    assert "minimum" not in api_schema["properties"]["limit"]
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        SearchFinancialProductsInput.model_validate(
            {
                "product_type": "deposit",
                "term_months": 0,
                "limit": 0,
            }
        )


def test_law_tool_returns_article_metadata_with_source_ids(monkeypatch) -> None:
    """법령 Tool의 검색 결과를 모델이 인용 가능한 근거 데이터로 변환"""
    monkeypatch.setattr(
        tool_module,
        "retrieve_articles",
        lambda **kwargs: [
            {
                "law_name": "예금자보호법",
                "article_no": "제32조",
                "effective_date": "20260102",
                "text": "보험금 지급 기준",
            }
        ],
    )
    tools = tool_module.create_agent_tools(
        encoder=object(),
        collection=object(),
    )
    law_tool = next(tool for tool in tools if tool.name == "search_law_articles")

    result = law_tool.invoke({"question": "예금자보호 한도를 알려주세요."})

    assert result == {
        "status": "ok",
        "articles": [
            {
                "source_id": "S1",
                "law_name": "예금자보호법",
                "article_no": "제32조",
                "effective_date": "20260102",
                "text": "보험금 지급 기준",
            }
        ],
    }


def test_product_tool_returns_ranked_deposit_candidates(monkeypatch) -> None:
    """상품 Tool의 정렬 결과와 비교 기준 반환"""
    monkeypatch.setattr(
        tool_module,
        "fetch_deposit_products",
        lambda: {
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
        },
    )
    tools = tool_module.create_agent_tools(
        encoder=object(),
        collection=object(),
    )
    product_tool = next(
        tool for tool in tools if tool.name == "search_financial_products"
    )

    result = product_tool.invoke(
        {
            "product_type": "deposit",
            "term_months": 12,
            "sort_by": "base_interest_rate",
            "limit": 3,
        }
    )

    assert result["status"] == "ok"
    assert result["comparison_basis"] == "base_interest_rate"
    assert result["products"][0]["product_name"] == "테스트예금"
    assert result["products"][0]["base_interest_rate"] == 3.1


def test_product_tool_returns_error_data_when_finlife_fails(monkeypatch) -> None:
    """Finlife 오류를 ToolNode 예외 대신 상태 데이터로 반환"""
    def raise_finlife_error() -> dict:
        raise RuntimeError("Finlife API error 101")

    monkeypatch.setattr(
        tool_module,
        "fetch_deposit_products",
        raise_finlife_error,
    )
    tools = tool_module.create_agent_tools(
        encoder=object(),
        collection=object(),
    )
    product_tool = next(
        tool for tool in tools if tool.name == "search_financial_products"
    )

    result = product_tool.invoke(
        {
            "product_type": "deposit",
            "term_months": 12,
            "sort_by": "base_interest_rate",
            "limit": 3,
        }
    )

    assert result == {
        "status": "error",
        "message": "Finlife 공시 정보를 불러오지 못했습니다.",
    }
