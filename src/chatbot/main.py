"""FastAPI 챗봇 API와 생성 backend 수명주기"""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field, TypeAdapter

from chatbot.agent.checkpoint import create_sqlite_checkpointer
from chatbot.agent.graph import create_multi_turn_agent_graph
from chatbot.agent.model import create_tool_calling_model
from chatbot.agent.tools import create_agent_tools
from chatbot.agent.turn_analysis import create_turn_analyzer
from chatbot.embedding import load_encoder
from chatbot.finlife import DepositProductOption, FinancialProductOption
from chatbot.generator_backend import create_generator
from chatbot.graph import (
    LawStatus,
    ProductStatus,
    QuestionRoute,
    create_rag_graph,
    create_routed_workflow_graph,
)
from chatbot.retriever import DEFAULT_TOP_K
from chatbot.settings import load_local_env
from chatbot.vectorstore import open_collection

LANGFEATHER_TRACE_NAME = "korean-chatbot-rag"
LANGFEATHER_WORKFLOW_TRACE_NAME = "korean-chatbot-routed-workflow"
LANGFEATHER_AGENT_TRACE_NAME = "korean-chatbot-agent"
LANGFEATHER_SHUTDOWN_TIMEOUT_SECONDS = 2.0
FINANCIAL_PRODUCT_OPTION_ADAPTER = TypeAdapter(FinancialProductOption)


def load_langfeather():
    """선택적 로컬 추적 SDK 로드"""
    try:
        import langfeather
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "LangFeather 추적에는 'uv sync --group tracing'이 필요합니다."
        ) from error
    return langfeather


class RagRequest(BaseModel):
    """법령 RAG에 전달할 사용자 질문 검증"""

    question: str = Field(min_length=1)


class RagSource(BaseModel):
    """RAG 답변에 사용한 법령 근거"""

    law_name: str
    article_no: str
    effective_date: str
    similarity: float


class RagResponse(BaseModel):
    """법령 RAG 답변과 검색 근거 형식 정의"""

    response: str
    sources: list[RagSource]
    generation_seconds: float


class WorkflowRequest(BaseModel):
    """Routed Workflow에 전달할 사용자 질문 검증"""

    question: str = Field(min_length=1)


class WorkflowResponse(BaseModel):
    """route별 답변과 법령·상품 실행 결과"""

    answer: str
    route: QuestionRoute
    law_status: LawStatus | None = None
    product_status: ProductStatus | None = None
    sources: list[RagSource]
    products: list[DepositProductOption]
    partial_failure: bool
    execution_seconds: float


class AgentRequest(BaseModel):
    """멀티턴 Agent에 전달할 thread와 현재 사용자 메시지"""

    thread_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class AgentSource(BaseModel):
    """Agent 법령 Tool이 반환한 인용 근거"""

    source_id: str
    law_name: str
    article_no: str
    effective_date: str


class AgentToolResult(BaseModel):
    """한 번의 Agent Tool 호출과 결과 상태"""

    name: str
    arguments: dict[str, object]
    status: str | None = None


class AgentResponse(BaseModel):
    """멀티턴 Agent의 답변과 실행 요약"""

    thread_id: str
    answer: str
    route: str
    product_preferences: dict[str, object] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    tools: list[AgentToolResult]
    sources: list[AgentSource]
    products: list[FinancialProductOption]
    execution_seconds: float


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


def prepare_workflow_resources(app: FastAPI) -> None:
    """공유 RAG 자원으로 Routed Workflow Graph 준비"""
    if hasattr(app.state, "routed_workflow_graph"):
        return

    prepare_rag_resources(app)
    workflow_graph = create_routed_workflow_graph(
        generator=app.state.generator,
        encoder=app.state.encoder,
        collection=app.state.collection,
        top_k=DEFAULT_TOP_K,
    )
    if app.state.langfeather_enabled:
        workflow_graph = app.state.langfeather_sdk.wrap_runnable(
            workflow_graph,
            name=LANGFEATHER_WORKFLOW_TRACE_NAME,
        )
    app.state.routed_workflow_graph = workflow_graph


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


def _agent_execution_details(
    messages: list,
) -> tuple[list[AgentToolResult], list[AgentSource], list[DepositProductOption]]:
    """Agent 메시지 누적값을 API용 Tool·근거·상품 목록으로 변환"""
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


def _agent_response(
    *,
    thread_id: str,
    graph_result: dict,
    execution_seconds: float,
) -> AgentResponse:
    """완료된 Agent Graph 상태를 API 응답 모델로 변환"""
    messages = graph_result["messages"]
    tools, sources, products = _agent_execution_details(messages)
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


def _sse_event(*, event: str, data: dict) -> str:
    """SSE event와 JSON data 한 묶음 생성"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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
            "routed_workflow_graph",
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


@app.post("/ask-rag/stream", response_class=StreamingResponse)
async def ask_rag_stream(
    payload: RagRequest, request: Request
) -> StreamingResponse:
    """법령 RAG 답변 조각을 순수 텍스트로 전송"""
    await asyncio.to_thread(prepare_rag_resources, request.app)

    graph_input = {
        "question": payload.question,
        "streaming": True,  # 그래프 노드에서 스트리밍 모드 활성화
    }

    return StreamingResponse(
        request.app.state.rag_graph.stream(
            input=graph_input,
            stream_mode="custom",
        ),
        media_type="text/plain; charset=utf-8",
    )


@app.post("/ask-workflow", response_model=WorkflowResponse)
async def ask_workflow(
    payload: WorkflowRequest,
    request: Request,
) -> WorkflowResponse:
    """질문을 route별 Workflow로 처리하고 전체 실행 결과 반환"""
    await asyncio.to_thread(prepare_workflow_resources, request.app)

    started_at = perf_counter()
    graph_result = await asyncio.to_thread(
        request.app.state.routed_workflow_graph.invoke,
        input={"question": payload.question},
    )
    execution_seconds = perf_counter() - started_at

    route = graph_result["route"]
    law_status = graph_result.get("law_status")
    product_status = graph_result.get("product_status")
    law_failed = law_status == "error"
    product_failed = product_status == "error"
    partial_failure = route == "mixed" and law_failed != product_failed

    return WorkflowResponse(
        answer=graph_result["answer"],
        route=route,
        law_status=law_status,
        product_status=product_status,
        sources=[
            RagSource(
                law_name=article["law_name"],
                article_no=article["article_no"],
                effective_date=article["effective_date"],
                similarity=article["similarity"],
            )
            for article in graph_result.get("articles", [])
        ],
        products=graph_result.get("products", []),
        partial_failure=partial_failure,
        execution_seconds=execution_seconds,
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
