"""Claude ChatModel 생성과 Tool 바인딩"""

import os
from collections.abc import Sequence

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from chatbot.agent.tools import AGENT_TOOL_SCHEMAS
from chatbot.generation.anthropic import (
    DEFAULT_MODEL_ID,
    MAX_OUTPUT_TOKENS,
    MODEL_ENV,
    TIMEOUT_ENV,
    TIMEOUT_SECONDS,
)

TOOL_CALLING_SYSTEM_PROMPT = """당신은 예·적금 금융 상담 Agent입니다.
- 법령 근거가 필요하면 search_law_articles를 선택하세요.
- 예금·적금 공시 상품 비교가 필요하면 search_financial_products를 선택하세요.
- Tool 결과를 직접 만들거나 조회하지 않은 정보를 추측하지 마세요.
- Tool이 필요하지 않은 간단한 대화에는 Tool을 호출하지 마세요."""


def create_tool_calling_model() -> ChatAnthropic:
    """현재 Claude 설정을 사용하는 LangChain ChatModel"""
    return ChatAnthropic(
        model=os.getenv(MODEL_ENV, DEFAULT_MODEL_ID),
        max_tokens=MAX_OUTPUT_TOKENS,
        timeout=float(os.getenv(TIMEOUT_ENV, str(TIMEOUT_SECONDS))),
        temperature=0,
    )


def invoke_tool_calling_model(
    *,
    model,
    question: str,
    tool_schemas: Sequence[type[BaseModel]] = AGENT_TOOL_SCHEMAS,
) -> AIMessage:
    """Tool이 연결된 ChatModel의 단일 AIMessage 요청"""
    model_with_tools = model.bind_tools(list(tool_schemas), strict=True)
    response = model_with_tools.invoke(
        [
            SystemMessage(content=TOOL_CALLING_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]
    )
    if not isinstance(response, AIMessage):
        raise TypeError("tool calling model must return AIMessage")
    return response
