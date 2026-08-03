"""SQLite를 사용하는 멀티턴 Clarify Agent 검증"""

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from chatbot.agent.checkpoint import create_sqlite_checkpointer
from chatbot.agent.graph import create_multi_turn_agent_graph
from chatbot.agent.turn_analysis import TurnIntent


class ScriptedToolCallingModel:
    """정해진 순서의 AIMessage를 반환하는 Tool 호출 모델 대역"""

    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = iter(responses)

    def bind_tools(self, tools, *, strict):
        return self

    def invoke(self, messages) -> AIMessage:
        return next(self.responses)


def _thread_config(thread_id: str) -> dict:
    """LangGraph thread 식별 runtime 설정"""
    return {"configurable": {"thread_id": thread_id}}


def test_clarify_turn_merges_conditions_then_calls_product_tool(tmp_path) -> None:
    """두 번째 답변의 기간을 저장된 상품 유형과 결합"""
    analyses = iter(
        [
            TurnIntent(intent="product"),
            TurnIntent(intent="product", product_type="deposit", term_months=12),
        ]
    )
    tool_calls = []

    def analyze_turn(*, message: str, previous_preferences: dict | None):
        return next(analyses)

    @tool("search_financial_products")
    def search_financial_products(
        product_type: str,
        term_months: int,
        sort_by: str,
        limit: int,
    ) -> dict:
        """정기예금 비교 후보"""
        tool_calls.append((product_type, term_months, sort_by, limit))
        return {"status": "ok", "products": [{"product_name": "테스트예금"}]}

    model = ScriptedToolCallingModel(
        [
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
                        "id": "product-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="12개월 정기예금 후보를 비교했어요."),
        ]
    )
    saver = create_sqlite_checkpointer(database_path=tmp_path / "langgraph.sqlite3")
    graph = create_multi_turn_agent_graph(
        model=model,
        tools=[search_financial_products],
        analyze_turn=analyze_turn,
        checkpointer=saver,
    )
    thread_config = _thread_config("conversation-1")

    first_result = graph.invoke(
        {"messages": [HumanMessage(content="금융상품 추천해 주세요.")]},
        config=thread_config,
    )
    second_result = graph.invoke(
        {"messages": [HumanMessage(content="12개월이요.")]},
        config=thread_config,
    )
    saver.conn.close()

    assert first_result["route"] == "clarify"
    assert first_result["missing_fields"] == ["product_type", "term_months"]
    assert first_result["messages"][-1].content == "예금과 적금 중 어떤 상품을 찾으시나요?"
    assert second_result["route"] == "ready"
    assert second_result["product_preferences"] == {
        "product_type": "deposit",
        "term_months": 12,
        "sort_by": "base_interest_rate",
        "limit": 3,
    }
    assert tool_calls == [("deposit", 12, "base_interest_rate", 3)]
    assert second_result["messages"][-1].content == "12개월 정기예금 후보를 비교했어요."


def test_clarify_turn_does_not_reuse_another_thread_preferences(tmp_path) -> None:
    """새 thread의 기간 답변은 이전 상품 조건을 사용하지 않음"""
    analyses = iter(
        [
            TurnIntent(intent="product", product_type="deposit"),
            TurnIntent(intent="product", term_months=12),
        ]
    )

    def analyze_turn(*, message: str, previous_preferences: dict | None):
        return next(analyses)

    saver = create_sqlite_checkpointer(database_path=tmp_path / "langgraph.sqlite3")
    graph = create_multi_turn_agent_graph(
        model=ScriptedToolCallingModel([]),
        tools=[],
        analyze_turn=analyze_turn,
        checkpointer=saver,
    )

    graph.invoke(
        {"messages": [HumanMessage(content="정기예금을 추천해 주세요.")]},
        config=_thread_config("conversation-1"),
    )
    result = graph.invoke(
        {"messages": [HumanMessage(content="12개월이요.")]},
        config=_thread_config("conversation-2"),
    )
    saver.conn.close()

    assert result["route"] == "clarify"
    assert result["missing_fields"] == ["product_type"]
    assert result["messages"][-1].content == "예금과 적금 중 어떤 상품을 찾으시나요?"


def test_clarify_turn_streams_fixed_question_as_token(tmp_path) -> None:
    """추가 질문도 SSE token으로 전달할 수 있는 Graph custom event 반환"""
    saver = create_sqlite_checkpointer(database_path=tmp_path / "langgraph.sqlite3")
    graph = create_multi_turn_agent_graph(
        model=ScriptedToolCallingModel([]),
        tools=[],
        analyze_turn=lambda **kwargs: TurnIntent(intent="product"),
        checkpointer=saver,
    )

    events = list(
        graph.stream(
            {
                "messages": [HumanMessage(content="금융상품 추천해 주세요.")],
                "streaming": True,
            },
            config=_thread_config("conversation-stream"),
            stream_mode="custom",
        )
    )
    saver.conn.close()

    assert events == [
        {"event": "status", "stage": "analyze"},
        {"event": "status", "stage": "clarify"},
        {
            "event": "token",
            "text": "예금과 적금 중 어떤 상품을 찾으시나요?",
        },
    ]
