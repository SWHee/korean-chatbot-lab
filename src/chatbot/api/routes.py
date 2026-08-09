"""금융 상담 FastAPI endpoint"""

import asyncio
from time import perf_counter

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from chatbot.api.models import (
    AgentRequest,
    AgentResponse,
    RagRequest,
    RagResponse,
    RagSource,
)
from chatbot.api.responses import build_agent_response, format_sse_event
from chatbot.api.resources import prepare_agent_resources, prepare_rag_resources

router = APIRouter()


@router.post("/ask-rag", response_model=RagResponse)
async def ask_rag(payload: RagRequest, request: Request) -> RagResponse:
    """법령 RAG로 질문에 답변하고 검색 근거 반환"""
    await asyncio.to_thread(prepare_rag_resources, request.app)

    started_at = perf_counter()
    graph_result = await asyncio.to_thread(
        request.app.state.rag_graph.invoke,
        input={"question": payload.question},
    )
    generation_seconds = perf_counter() - started_at

    return RagResponse(
        response=graph_result["answer"],
        sources=[
            RagSource(
                law_name=article["law_name"],
                article_no=article["article_no"],
                effective_date=article["effective_date"],
                similarity=article["similarity"],
            )
            for article in graph_result["articles"]
        ],
        generation_seconds=generation_seconds,
    )


@router.post("/ask-agent", response_model=AgentResponse)
async def ask_agent(payload: AgentRequest, request: Request) -> AgentResponse:
    """같은 thread의 조건을 이어가는 비스트리밍 Agent 실행"""
    await asyncio.to_thread(prepare_agent_resources, request.app)

    started_at = perf_counter()
    graph_result = await asyncio.to_thread(
        request.app.state.agent_graph.invoke,
        input={
            "messages": [HumanMessage(content=payload.message)],
            "streaming": False,
        },
        config={"configurable": {"thread_id": payload.thread_id}},
    )

    return build_agent_response(
        thread_id=payload.thread_id,
        graph_result=graph_result,
        execution_seconds=perf_counter() - started_at,
    )


@router.post("/ask-agent/stream", response_class=StreamingResponse)
async def ask_agent_stream(
    payload: AgentRequest,
    request: Request,
) -> StreamingResponse:
    """Agent 진행 상태·답변 조각·최종 결과를 SSE로 전달"""
    await asyncio.to_thread(prepare_agent_resources, request.app)

    def stream_events():
        started_at = perf_counter()
        graph_result = None
        try:
            for mode, chunk in request.app.state.agent_graph.stream(
                input={
                    "messages": [HumanMessage(content=payload.message)],
                    "streaming": True,
                },
                config={"configurable": {"thread_id": payload.thread_id}},
                stream_mode=["custom", "values"],
            ):
                if mode == "custom":
                    event = chunk.get("event", "status")
                    yield format_sse_event(
                        event=event,
                        data={
                            key: value
                            for key, value in chunk.items()
                            if key != "event"
                        },
                    )
                elif mode == "values":
                    graph_result = chunk

            if graph_result is None:
                raise RuntimeError("agent stream produced no final state")
            response = build_agent_response(
                thread_id=payload.thread_id,
                graph_result=graph_result,
                execution_seconds=perf_counter() - started_at,
            )
            yield format_sse_event(
                event="result",
                data=response.model_dump(mode="json"),
            )
        except Exception:
            yield format_sse_event(
                event="error",
                data={
                    "message": "Agent 실행 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요."
                },
            )

    return StreamingResponse(stream_events(), media_type="text/event-stream")
