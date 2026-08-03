"""ToolNode 기반 단일 요청 Agent loop 검증"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from chatbot.agent.graph import (
    AGENT_CALL_LIMIT_MESSAGE,
    AGENT_REPEAT_CALL_MESSAGE,
    MAX_AGENT_TOOL_CALLS,
    create_agent_loop_graph,
)


class ScriptedToolCallingModel:
    """정해진 순서의 AIMessage를 반환하는 Tool 호출 모델 대역"""

    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = iter(responses)
        self.bound_tools = []
        self.strict = None
        self.requests = []

    def bind_tools(self, tools, *, strict):
        self.bound_tools = tools
        self.strict = strict
        return self

    def invoke(self, messages) -> AIMessage:
        self.requests.append(messages)
        return next(self.responses)


def _tool_call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": args,
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def test_agent_loop_executes_law_tool_then_returns_final_answer() -> None:
    """법령 Tool 결과를 본 뒤 모델의 최종 답변으로 종료"""
    calls = []

    @tool("search_law_articles")
    def search_law_articles(question: str) -> dict:
        """법령 검색 결과"""
        calls.append(question)
        return {"status": "ok", "articles": [{"article_no": "제32조"}]}

    model = ScriptedToolCallingModel(
        [
            _tool_call(
                "search_law_articles",
                {"question": "예금자보호 한도는 얼마인가요?"},
                "law-1",
            ),
            AIMessage(content="예금자보호 한도는 법령 근거를 확인해 안내드릴게요."),
        ]
    )
    graph = create_agent_loop_graph(model=model, tools=[search_law_articles])

    result = graph.invoke(
        {"messages": [HumanMessage(content="예금자보호 한도를 알려주세요.")]}
    )

    assert calls == ["예금자보호 한도는 얼마인가요?"]
    assert result["tool_call_count"] == 1
    assert isinstance(result["messages"][-2], ToolMessage)
    assert result["messages"][-1].content == (
        "예금자보호 한도는 법령 근거를 확인해 안내드릴게요."
    )


def test_agent_loop_executes_product_tool_then_returns_final_answer() -> None:
    """상품 Tool 결과를 본 뒤 모델의 최종 답변으로 종료"""
    calls = []

    @tool("search_financial_products")
    def search_financial_products(
        product_type: str,
        term_months: int,
        sort_by: str,
        limit: int,
    ) -> dict:
        """상품 비교 결과"""
        calls.append((product_type, term_months, sort_by, limit))
        return {"status": "ok", "products": [{"product_name": "테스트예금"}]}

    model = ScriptedToolCallingModel(
        [
            _tool_call(
                "search_financial_products",
                {
                    "product_type": "deposit",
                    "term_months": 12,
                    "sort_by": "base_interest_rate",
                    "limit": 3,
                },
                "product-1",
            ),
            AIMessage(content="12개월 정기예금 후보를 비교해 드릴게요."),
        ]
    )
    graph = create_agent_loop_graph(
        model=model,
        tools=[search_financial_products],
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content="12개월 정기예금을 비교해 주세요.")]}
    )

    assert calls == [("deposit", 12, "base_interest_rate", 3)]
    assert result["tool_call_count"] == 1
    assert result["messages"][-1].content == "12개월 정기예금 후보를 비교해 드릴게요."


def test_agent_loop_executes_two_tools_for_mixed_question() -> None:
    """한 AIMessage의 법령·상품 Tool 요청을 모두 실행"""
    calls = []

    @tool("search_law_articles")
    def search_law_articles(question: str) -> dict:
        """법령 검색 결과"""
        calls.append("law")
        return {"status": "ok", "articles": []}

    @tool("search_financial_products")
    def search_financial_products(
        product_type: str,
        term_months: int,
        sort_by: str,
        limit: int,
    ) -> dict:
        """상품 비교 결과"""
        calls.append("product")
        return {"status": "ok", "products": []}

    model = ScriptedToolCallingModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_law_articles",
                        "args": {"question": "예금자보호 한도"},
                        "id": "law-1",
                        "type": "tool_call",
                    },
                    {
                        "name": "search_financial_products",
                        "args": {
                            "product_type": "deposit",
                            "term_months": 12,
                            "sort_by": "base_interest_rate",
                            "limit": 3,
                        },
                        "id": "product-1",
                        "type": "tool_call",
                    },
                ],
            ),
            AIMessage(content="법령과 상품 후보를 함께 확인했습니다."),
        ]
    )
    graph = create_agent_loop_graph(
        model=model,
        tools=[search_law_articles, search_financial_products],
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content="12개월 예금과 예금자보호를 알려주세요.")]}
    )

    assert set(calls) == {"law", "product"}
    assert result["tool_call_count"] == 2
    assert result["messages"][-1].content == "법령과 상품 후보를 함께 확인했습니다."


def test_agent_loop_finishes_when_tool_is_unnecessary() -> None:
    """Tool 요청이 없는 응답은 반복 없이 종료"""
    model = ScriptedToolCallingModel([AIMessage(content="안녕하세요. 무엇을 도와드릴까요?")])
    graph = create_agent_loop_graph(model=model, tools=[])

    result = graph.invoke({"messages": [HumanMessage(content="안녕하세요.")]})

    assert result.get("tool_call_count", 0) == 0
    assert result["messages"][-1].content == "안녕하세요. 무엇을 도와드릴까요?"


def test_agent_loop_returns_final_answer_after_tool_error_data() -> None:
    """Tool 오류 상태도 ToolMessage로 전달한 뒤 최종 답변 생성"""

    @tool("search_financial_products")
    def search_financial_products(
        product_type: str,
        term_months: int,
        sort_by: str,
        limit: int,
    ) -> dict:
        """상품 비교 오류"""
        return {"status": "error", "message": "공시 정보를 불러오지 못했습니다."}

    model = ScriptedToolCallingModel(
        [
            _tool_call(
                "search_financial_products",
                {
                    "product_type": "deposit",
                    "term_months": 12,
                    "sort_by": "base_interest_rate",
                    "limit": 3,
                },
                "product-1",
            ),
            AIMessage(content="지금은 상품 공시 정보를 확인할 수 없어요."),
        ]
    )
    graph = create_agent_loop_graph(
        model=model,
        tools=[search_financial_products],
    )

    result = graph.invoke(
        {"messages": [HumanMessage(content="12개월 정기예금을 비교해 주세요.")]}
    )

    assert isinstance(result["messages"][-2], ToolMessage)
    assert result["messages"][-1].content == "지금은 상품 공시 정보를 확인할 수 없어요."


def test_agent_loop_stops_repeated_tool_call_before_second_execution() -> None:
    """같은 Tool과 인자를 다시 요청하면 안전 안내로 종료"""
    calls = []

    @tool("search_law_articles")
    def search_law_articles(question: str) -> dict:
        """법령 검색 결과"""
        calls.append(question)
        return {"status": "ok", "articles": []}

    repeated_args = {"question": "예금자보호 한도는 얼마인가요?"}
    model = ScriptedToolCallingModel(
        [
            _tool_call("search_law_articles", repeated_args, "law-1"),
            _tool_call("search_law_articles", repeated_args, "law-2"),
        ]
    )
    graph = create_agent_loop_graph(model=model, tools=[search_law_articles])

    result = graph.invoke(
        {"messages": [HumanMessage(content="예금자보호 한도를 알려주세요.")]}
    )

    assert calls == ["예금자보호 한도는 얼마인가요?"]
    assert result["tool_call_count"] == 1
    assert result["messages"][-1].content == AGENT_REPEAT_CALL_MESSAGE


def test_agent_loop_stops_when_tool_call_limit_is_reached() -> None:
    """이름 있는 호출 상한을 넘는 새 Tool 요청 차단"""
    calls = []

    @tool("search_law_articles")
    def search_law_articles(question: str) -> dict:
        """법령 검색 결과"""
        calls.append(question)
        return {"status": "ok", "articles": []}

    responses = [
        _tool_call(
            "search_law_articles",
            {"question": f"질문 {index}"},
            f"law-{index}",
        )
        for index in range(MAX_AGENT_TOOL_CALLS + 1)
    ]
    model = ScriptedToolCallingModel(responses)
    graph = create_agent_loop_graph(model=model, tools=[search_law_articles])

    result = graph.invoke({"messages": [HumanMessage(content="법령을 찾아주세요.")]})

    assert calls == [f"질문 {index}" for index in range(MAX_AGENT_TOOL_CALLS)]
    assert result["tool_call_count"] == MAX_AGENT_TOOL_CALLS
    assert result["messages"][-1].content == AGENT_CALL_LIMIT_MESSAGE
