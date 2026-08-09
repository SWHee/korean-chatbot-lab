"""LangGraph 실행 결과의 FastAPI 응답 변환"""

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import TypeAdapter

from chatbot.api.models import AgentResponse, AgentSource, AgentToolResult
from chatbot.products import FinancialProductOption

FINANCIAL_PRODUCT_OPTION_ADAPTER = TypeAdapter(FinancialProductOption)


def extract_agent_execution_details(
    messages: list,
) -> tuple[list[AgentToolResult], list[AgentSource], list[FinancialProductOption]]:
    """현재 턴의 Tool 호출을 API용 실행 세부 정보로 변환"""
    latest_human_index = max(
        index
        for index, message in enumerate(messages)
        if isinstance(message, HumanMessage)
    )
    current_turn_messages = messages[latest_human_index + 1 :]
    calls_by_id = {
        call["id"]: call
        for message in current_turn_messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    }
    tools = []
    sources = []
    products = []

    for message in current_turn_messages:
        if not isinstance(message, ToolMessage):
            continue
        tool_call = calls_by_id.get(message.tool_call_id, {})
        try:
            result = json.loads(message.content)
        except (TypeError, json.JSONDecodeError):
            result = {}
        tools.append(
            AgentToolResult(
                name=message.name or tool_call.get("name", "unknown"),
                arguments=tool_call.get("args", {}),
                status=result.get("status"),
            )
        )
        sources.extend(
            AgentSource.model_validate(article)
            for article in result.get("articles", [])
        )
        product_type = tool_call.get("args", {}).get("product_type", "deposit")
        products.extend(
            FINANCIAL_PRODUCT_OPTION_ADAPTER.validate_python(
                {"product_type": product_type, **product}
            )
            for product in result.get("products", [])
        )

    return tools, sources, products


def build_agent_response(
    *,
    thread_id: str,
    graph_result: dict,
    execution_seconds: float,
) -> AgentResponse:
    """완료된 Agent Graph 상태를 API 응답 모델로 변환"""
    messages = graph_result["messages"]
    tools, sources, products = extract_agent_execution_details(messages)
    return AgentResponse(
        thread_id=thread_id,
        answer=messages[-1].text,
        route=graph_result["route"],
        product_preferences=graph_result.get("product_preferences", {}),
        missing_fields=graph_result.get("missing_fields", []),
        tools=tools,
        sources=sources,
        products=products,
        execution_seconds=execution_seconds,
    )


def format_sse_event(*, event: str, data: dict) -> str:
    """SSE event와 JSON data 한 묶음 생성"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
