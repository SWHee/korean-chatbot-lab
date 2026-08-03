"""ToolNode 기반 단일 요청 Agent loop"""

import json
from typing import Literal, NotRequired, TypedDict

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from chatbot.agent.model import TOOL_CALLING_SYSTEM_PROMPT


MAX_AGENT_TOOL_CALLS = 4
AGENT_REPEAT_CALL_MESSAGE = (
    "같은 조회 요청이 반복되어 안내를 잠시 멈췄어요. "
    "질문 조건을 조금 바꿔 다시 알려주세요."
)
AGENT_CALL_LIMIT_MESSAGE = (
    "한 질문에서 조회 가능한 횟수를 모두 사용했어요. "
    "원하는 상품 종류나 기간을 더 구체적으로 알려주세요."
)

AgentNextNode = Literal["record_tool_calls", "stop_repeated_call", "__end__"]


class AgentState(MessagesState):
    """대화 메시지와 이번 요청의 Tool 호출 기록"""

    tool_call_count: NotRequired[int]
    tool_call_signatures: NotRequired[list[str]]


def _tool_call_signature(tool_call: dict) -> str:
    """Tool 이름과 인자를 비교할 수 있는 고정 문자열"""
    return json.dumps(
        {
            "name": tool_call["name"],
            "args": tool_call["args"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def create_agent_loop_graph(
    *,
    model,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Tool 결과를 본 뒤 최종 답변까지 이어지는 Agent Graph"""
    model_with_tools = model.bind_tools(tools, strict=True)

    def agent_model_node(state: AgentState) -> dict:
        response = model_with_tools.invoke(
            [
                SystemMessage(content=TOOL_CALLING_SYSTEM_PROMPT),
                *state["messages"],
            ]
        )
        if not isinstance(response, AIMessage):
            raise TypeError("agent model must return AIMessage")
        return {"messages": [response]}

    def route_after_agent(state: AgentState) -> AgentNextNode:
        latest_message = state["messages"][-1]  # 최신 AIMessage
        if not isinstance(latest_message, AIMessage):
            raise TypeError("agent node must append AIMessage")
        if not latest_message.tool_calls:
            return END

        signatures = [
            _tool_call_signature(tool_call)
            for tool_call in latest_message.tool_calls
        ]
        previous_signatures = state.get("tool_call_signatures", [])
        has_repeated_call = (
            len(signatures) != len(set(signatures))
            or any(signature in previous_signatures for signature in signatures)
        )
        if has_repeated_call:
            return "stop_repeated_call"

        tool_call_count = state.get("tool_call_count", 0)
        if tool_call_count + len(signatures) > MAX_AGENT_TOOL_CALLS:
            return "stop_repeated_call"
        return "record_tool_calls"

    def record_tool_calls_node(state: AgentState) -> dict:
        latest_message = state["messages"][-1]
        if not isinstance(latest_message, AIMessage):
            raise TypeError("agent node must append AIMessage")
        signatures = [
            _tool_call_signature(tool_call)
            for tool_call in latest_message.tool_calls
        ]
        return {
            "tool_call_count": state.get("tool_call_count", 0) + len(signatures),
            "tool_call_signatures": [
                *state.get("tool_call_signatures", []),
                *signatures,
            ],
        }

    def stop_repeated_call_node(state: AgentState) -> dict:
        latest_message = state["messages"][-1]
        tool_call_count = state.get("tool_call_count", 0)
        message = (
            AGENT_CALL_LIMIT_MESSAGE
            if isinstance(latest_message, AIMessage)
            and tool_call_count + len(latest_message.tool_calls) > MAX_AGENT_TOOL_CALLS
            else AGENT_REPEAT_CALL_MESSAGE
        )
        return {"messages": [AIMessage(content=message)]}

    builder = StateGraph(AgentState)

    builder.add_node("agent_model", agent_model_node)
    builder.add_node("record_tool_calls", record_tool_calls_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("stop_repeated_call", stop_repeated_call_node)

    builder.add_edge(START, "agent_model")
    builder.add_conditional_edges(
        "agent_model",
        route_after_agent,
        {
            "record_tool_calls": "record_tool_calls",
            "stop_repeated_call": "stop_repeated_call",
            END: END,
        },
    )
    # 기록 Node는 메시지를 바꾸지 않아 ToolNode가 직전 AI Tool 요청을 실행
    builder.add_edge("record_tool_calls", "tools")
    builder.add_edge("tools", "agent_model")
    builder.add_edge("stop_repeated_call", END)

    return builder.compile(checkpointer=checkpointer)
