"""FastAPI 챗봇 API와 생성 backend 수명주기"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from chatbot.agent.checkpoint import create_sqlite_checkpointer
from chatbot.agent.graph import create_multi_turn_agent_graph
from chatbot.agent.model import create_tool_calling_model
from chatbot.agent.tools import create_agent_tools
from chatbot.agent.turn_analysis import create_turn_analyzer
from chatbot.api.models import (
    AgentRequest,
    AgentResponse,
    RagRequest,
    RagResponse,
    RagSource,
)
from chatbot.api.responses import (
    build_agent_response as _agent_response,
    extract_agent_execution_details as _agent_execution_details,
    format_sse_event as _sse_event,
)
from chatbot.embedding import load_encoder
from chatbot.generator_backend import create_generator
from chatbot.graph import create_rag_graph
from chatbot.retriever import DEFAULT_TOP_K
from chatbot.settings import load_local_env
from chatbot.vectorstore import open_collection

LANGFEATHER_TRACE_NAME = "korean-chatbot-rag"
LANGFEATHER_AGENT_TRACE_NAME = "korean-chatbot-agent"
LANGFEATHER_SHUTDOWN_TIMEOUT_SECONDS = 2.0


def load_langfeather():
    """선택적 로컬 추적 SDK 로드"""
    try:
        import langfeather
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "LangFeather 추적에는 'uv sync --group tracing'이 필요합니다."
        ) from error
    return langfeather


def prepare_rag_resources(app: FastAPI) -> None:
    """필요 시 RAG 임베딩 모델과 벡터스토어 준비"""
    if not hasattr(app.state, "encoder"):
        app.state.encoder = load_encoder()
    if not hasattr(app.state, "collection"):
        app.state.collection = open_collection()
    if not hasattr(app.state, "rag_graph"):
        rag_graph = create_rag_graph(
            generator=app.state.generator,
            encoder=app.state.encoder,
            collection=app.state.collection,
            top_k=DEFAULT_TOP_K,
        )
        app.state.langfeather_enabled = (
            os.getenv("LANGFEATHER_ENABLED", "false").strip().lower() == "true"
        )
        if app.state.langfeather_enabled:
            langfeather_sdk = load_langfeather()
            langfeather_sdk.configure(
                endpoint=os.getenv("LANGFEATHER_ENDPOINT") or None,
            )
            # 그래프를 LangFeather 추적 가능한 Runnable로 래핑
            rag_graph = langfeather_sdk.wrap_runnable(
                rag_graph,
                name=LANGFEATHER_TRACE_NAME,
            )
            app.state.langfeather_sdk = langfeather_sdk
        app.state.rag_graph = rag_graph


def prepare_agent_resources(app: FastAPI) -> None:
    """공유 자원과 SQLite Checkpointer로 멀티턴 Agent Graph 준비"""
    if hasattr(app.state, "agent_graph"):
        return

    prepare_rag_resources(app)
    agent_checkpointer = create_sqlite_checkpointer()
    agent_graph = create_multi_turn_agent_graph(
        model=create_tool_calling_model(),
        tools=create_agent_tools(
            encoder=app.state.encoder,
            collection=app.state.collection,
            top_k=DEFAULT_TOP_K,
        ),
        analyze_turn=create_turn_analyzer(generator=app.state.generator),
        checkpointer=agent_checkpointer,
    )
    if app.state.langfeather_enabled:
        agent_graph = app.state.langfeather_sdk.wrap_runnable(
            agent_graph,
            name=LANGFEATHER_AGENT_TRACE_NAME,
        )
    app.state.agent_checkpointer = agent_checkpointer
    app.state.agent_graph = agent_graph


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 선택한 backend의 생성기를 준비하고 종료 시 해제"""
    load_local_env()
    app.state.generator = create_generator()
    try:
        yield
    finally:
        langfeather_sdk = getattr(app.state, "langfeather_sdk", None)
        if getattr(app.state, "langfeather_enabled", False) and langfeather_sdk:
            await asyncio.to_thread(
                langfeather_sdk.shutdown,
                timeout=LANGFEATHER_SHUTDOWN_TIMEOUT_SECONDS,
            )
        agent_checkpointer = getattr(app.state, "agent_checkpointer", None)
        if agent_checkpointer:
            agent_checkpointer.conn.close()
        for name in (
            "generator",
            "encoder",
            "collection",
            "rag_graph",
            "agent_graph",
            "agent_checkpointer",
            "langfeather_enabled",
            "langfeather_sdk",
        ):
            if hasattr(app.state, name):
                delattr(app.state, name)


app = FastAPI(
    title="Korean Chatbot",
    lifespan=lifespan,
)


@app.post("/ask-rag", response_model=RagResponse)
async def ask_rag(payload: RagRequest, request: Request) -> RagResponse:
    """법령 RAG로 질문에 답변하고 검색 근거 반환"""
    await asyncio.to_thread(prepare_rag_resources, request.app)

    started_at = perf_counter()
    graph_input = {"question": payload.question}
    graph_result = await asyncio.to_thread(
        request.app.state.rag_graph.invoke,
        input=graph_input,
    )
    generation_seconds = perf_counter() - started_at

    articles = graph_result["articles"]
    response = graph_result["answer"]

    return RagResponse(
        response=response,
        sources=[
            RagSource(
                law_name=article["law_name"],
                article_no=article["article_no"],
                effective_date=article["effective_date"],
                similarity=article["similarity"],
            )
            for article in articles
        ],
        generation_seconds=generation_seconds,
    )


@app.post("/ask-agent", response_model=AgentResponse)
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
    execution_seconds = perf_counter() - started_at

    return _agent_response(
        thread_id=payload.thread_id,
        graph_result=graph_result,
        execution_seconds=execution_seconds,
    )


@app.post("/ask-agent/stream", response_class=StreamingResponse)
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
                    yield _sse_event(
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
            response = _agent_response(
                thread_id=payload.thread_id,
                graph_result=graph_result,
                execution_seconds=perf_counter() - started_at,
            )
            yield _sse_event(event="result", data=response.model_dump(mode="json"))
        except Exception:
            yield _sse_event(
                event="error",
                data={
                    "message": "Agent 실행 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요."
                },
            )

    return StreamingResponse(stream_events(), media_type="text/event-stream")
