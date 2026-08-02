"""FastAPI 챗봇 API와 생성 backend 수명주기"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from chatbot.embedding import load_encoder
from chatbot.finlife import DepositProductOption
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
        for name in (
            "generator",
            "encoder",
            "collection",
            "rag_graph",
            "routed_workflow_graph",
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
