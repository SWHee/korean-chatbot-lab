"""Agent Tool 입력 계약 검증"""

import pytest
from pydantic import ValidationError

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
