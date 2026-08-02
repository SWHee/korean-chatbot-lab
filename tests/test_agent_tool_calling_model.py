"""Claude Tool Calling 단독 경계 검증"""

from langchain_core.messages import AIMessage

from chatbot.agent.model import invoke_tool_calling_model
from chatbot.agent.tools import AGENT_TOOL_SCHEMAS, SearchLawArticlesInput


class FakeToolCallingModel:
    """바인딩한 Tool과 고정 AIMessage를 반환하는 ChatModel 대역"""

    def __init__(self, response: AIMessage) -> None:
        self.response = response
        self.bound_tool_names = []
        self.strict = None

    def bind_tools(self, tools, *, strict):
        self.bound_tool_names = [
            tool.model_json_schema()["title"] for tool in tools
        ]
        self.strict = strict
        return self

    def invoke(self, messages) -> AIMessage:
        return self.response


def test_tool_calling_model_returns_law_tool_name_and_arguments() -> None:
    """법령 질문의 표준 AIMessage tool_calls 확인"""
    model = FakeToolCallingModel(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_law_articles",
                    "args": {"question": "예금자보호 한도는 얼마인가요?"},
                    "id": "law-call",
                    "type": "tool_call",
                }
            ],
        )
    )

    response = invoke_tool_calling_model(
        model=model,
        question="예금자보호 한도를 알려주세요.",
        tool_schemas=(SearchLawArticlesInput,),
    )

    assert response.tool_calls[0]["name"] == "search_law_articles"
    assert response.tool_calls[0]["args"] == {
        "question": "예금자보호 한도는 얼마인가요?"
    }
    assert model.bound_tool_names == ["search_law_articles"]
    assert model.strict is True


def test_tool_calling_model_binds_law_and_product_tools() -> None:
    """두 Tool 중 상품 질문에 필요한 호출 결과 확인"""
    model = FakeToolCallingModel(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_financial_products",
                    "args": {
                        "product_type": "deposit",
                        "term_months": 12,
                        "sort_by": "base_interest_rate",
                        "limit": 3,
                    },
                    "id": "product-call",
                    "type": "tool_call",
                }
            ],
        )
    )

    response = invoke_tool_calling_model(
        model=model,
        question="12개월 정기예금을 비교해 주세요.",
    )

    assert response.tool_calls[0]["name"] == "search_financial_products"
    assert model.bound_tool_names == [
        "search_law_articles",
        "search_financial_products",
    ]


def test_tool_calling_model_keeps_empty_calls_when_tool_is_unnecessary() -> None:
    """Tool이 필요 없는 대화의 빈 호출 목록 유지"""
    model = FakeToolCallingModel(AIMessage(content="안녕하세요!", tool_calls=[]))

    response = invoke_tool_calling_model(
        model=model,
        question="안녕하세요.",
        tool_schemas=AGENT_TOOL_SCHEMAS,
    )

    assert response.tool_calls == []
