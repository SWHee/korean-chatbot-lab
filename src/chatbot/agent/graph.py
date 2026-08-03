"""ToolNode 기반 단일 요청 Agent loop"""

import json
from collections.abc import Callable
from typing import Literal, NotRequired, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from chatbot.agent.model import TOOL_CALLING_SYSTEM_PROMPT
from chatbot.agent.turn_analysis import TurnIntent
from chatbot.graph import OUT_OF_SCOPE_MESSAGE, ProductFilters


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
MultiTurnNextNode = Literal["clarify", "out_of_scope", "agent_model"]


class AgentState(MessagesState):
    """대화 메시지와 이번 요청의 Tool 호출 기록"""

    tool_call_count: NotRequired[int]
    tool_call_signatures: NotRequired[list[str]]
    streaming: NotRequired[bool]


class MultiTurnAgentState(AgentState):
    """대화 메시지와 턴 사이에 유지할 상품 조건"""

    product_preferences: NotRequired[dict[str, object]]
    missing_fields: NotRequired[list[str]]
    route: NotRequired[Literal["clarify", "out_of_scope", "ready"]]
    clarifying_question: NotRequired[str | None]


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


def _add_agent_loop_nodes(*, builder, model, tools: list[BaseTool]) -> None:
    """Tool 호출과 최종 답변 반복 Node·Edge 추가"""
    model_with_tools = model.bind_tools(tools, strict=True)

    def stream_model_response(messages: list) -> AIMessage:
        """ChatModel 조각을 누적하고 텍스트를 custom stream으로 전달"""
        write_event = get_stream_writer()
        response_chunk = None
        for chunk in model_with_tools.stream(messages):
            response_chunk = chunk if response_chunk is None else response_chunk + chunk
            if chunk.text:
                write_event({"event": "token", "text": chunk.text})
        if response_chunk is None:
            raise ValueError("streaming agent model returned no chunks")
        return AIMessage(
            content=response_chunk.content,
            tool_calls=response_chunk.tool_calls,
            additional_kwargs=response_chunk.additional_kwargs,
            response_metadata=response_chunk.response_metadata,
            id=response_chunk.id,
        )

    def agent_model_node(state: AgentState) -> dict:
        messages = [
            SystemMessage(content=TOOL_CALLING_SYSTEM_PROMPT),
            *state["messages"],
        ]
        if state.get("streaming", False):
            get_stream_writer()({"event": "status", "stage": "generate"})
            response = stream_model_response(messages)
        else:
            response = model_with_tools.invoke(messages)
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
        if state.get("streaming", False):
            get_stream_writer()(
                {
                    "event": "status",
                    "stage": "tools",
                    "tools": [tool_call["name"] for tool_call in latest_message.tool_calls],
                }
            )
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
        if state.get("streaming", False):
            get_stream_writer()({"event": "token", "text": message})
        return {"messages": [AIMessage(content=message)]}

    builder.add_node("agent_model", agent_model_node)
    builder.add_node("record_tool_calls", record_tool_calls_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("stop_repeated_call", stop_repeated_call_node)

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


def create_agent_loop_graph(
    *,
    model,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Tool 결과를 본 뒤 최종 답변까지 이어지는 Agent Graph"""
    builder = StateGraph(AgentState)
    _add_agent_loop_nodes(builder=builder, model=model, tools=tools)

    builder.add_edge(START, "agent_model")

    return builder.compile(checkpointer=checkpointer)


def _merge_product_preferences(
    *,
    previous_preferences: dict[str, object] | None,
    intent: TurnIntent,
) -> dict[str, object]:
    """기존 조건에 현재 메시지의 명시 조건을 병합"""
    merged_preferences = dict(previous_preferences or {})
    merged_preferences.update(intent.model_dump(exclude_none=True, exclude={"intent"}))
    return ProductFilters.model_validate(merged_preferences).model_dump()


def _clarifying_question(missing_fields: list[str]) -> str:
    """가장 먼저 필요한 상품 조건 한 가지 질문"""
    if "product_type" in missing_fields:
        return "예금과 적금 중 어떤 상품을 찾으시나요?"
    return "몇 개월 동안 가입할 상품을 찾으시나요?"


def create_multi_turn_agent_graph(
    *,
    model,
    tools: list[BaseTool],
    analyze_turn: Callable[..., TurnIntent],
    checkpointer: BaseCheckpointSaver,
):
    """SQLite thread의 상품 조건을 이어가는 Clarify Agent Graph"""

    def analyze_turn_node(state: MultiTurnAgentState) -> dict:
        latest_message = state["messages"][-1]
        if not isinstance(latest_message, HumanMessage):
            raise TypeError("multi-turn graph requires latest HumanMessage")

        if state.get("streaming", False):
            get_stream_writer()({"event": "status", "stage": "analyze"})
        intent = analyze_turn(
            message=str(latest_message.content),
            previous_preferences=state.get("product_preferences"),
        )
        # 이전 Tool 실행 기록은 다음 사용자 턴에 적용하지 않음
        result: dict[str, object] = {
            "tool_call_count": 0,
            "tool_call_signatures": [],
        }
        if intent.intent == "out_of_scope":
            return result | {"route": "out_of_scope"}
        if intent.intent not in {"product", "mixed"}:
            return result | {"route": "ready"}

        preferences = _merge_product_preferences(
            previous_preferences=state.get("product_preferences"),
            intent=intent,
        )
        missing_fields = ProductFilters.model_validate(
            preferences
        ).missing_required_fields()
        if missing_fields:
            return result | {
                "route": "clarify",
                "product_preferences": preferences,
                "missing_fields": missing_fields,
                "clarifying_question": _clarifying_question(missing_fields),
            }
        return result | {
            "route": "ready",
            "product_preferences": preferences,
            "missing_fields": [],
            "clarifying_question": None,
        }

    def route_after_analysis(state: MultiTurnAgentState) -> MultiTurnNextNode:
        return state["route"]

    def ask_clarifying_question_node(state: MultiTurnAgentState) -> dict:
        question = state["clarifying_question"]
        if state.get("streaming", False):
            get_stream_writer()({"event": "status", "stage": "clarify"})
            get_stream_writer()({"event": "token", "text": question})
        return {"messages": [AIMessage(content=question)]}

    def explain_scope_node(state: MultiTurnAgentState) -> dict:
        if state.get("streaming", False):
            get_stream_writer()({"event": "status", "stage": "out_of_scope"})
            get_stream_writer()({"event": "token", "text": OUT_OF_SCOPE_MESSAGE})
        return {"messages": [AIMessage(content=OUT_OF_SCOPE_MESSAGE)]}

    builder = StateGraph(MultiTurnAgentState)
    builder.add_node("analyze_turn", analyze_turn_node)
    builder.add_node("ask_clarifying_question", ask_clarifying_question_node)
    builder.add_node("explain_scope", explain_scope_node)
    _add_agent_loop_nodes(builder=builder, model=model, tools=tools)

    builder.add_edge(START, "analyze_turn")
    builder.add_conditional_edges(
        "analyze_turn",
        route_after_analysis,
        {
            "clarify": "ask_clarifying_question",
            "out_of_scope": "explain_scope",
            "ready": "agent_model",
        },
    )
    builder.add_edge("ask_clarifying_question", END)
    builder.add_edge("explain_scope", END)

    return builder.compile(checkpointer=checkpointer)
