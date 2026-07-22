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
from chatbot.ollama_generator import OllamaGenerator
from chatbot.rag import answer_question, stream_answer_question
from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles
from chatbot.settings import load_local_env
from chatbot.vectorstore import open_collection


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


def prepare_rag_resources(app: FastAPI) -> None:
    """필요 시 RAG 임베딩 모델과 벡터스토어 준비"""
    if not hasattr(app.state, "encoder"):
        app.state.encoder = load_encoder()
    if not hasattr(app.state, "collection"):
        app.state.collection = open_collection()


async def retrieve_rag_articles(request: Request, question: str) -> list[dict]:
    """두 RAG endpoint가 공유하는 상위 법령 조문 검색"""
    return await asyncio.to_thread(
        retrieve_articles,
        encoder=request.app.state.encoder,
        collection=request.app.state.collection,
        question=question,
        top_k=DEFAULT_TOP_K,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 선택한 backend의 생성기를 준비하고 종료 시 해제"""
    load_local_env()
    backend = os.getenv("CHATBOT_BACKEND", "ollama")
    if backend == "ollama":
        app.state.generator = OllamaGenerator()
    elif backend == "hf":
        # torch 적재 비용 때문에 hf 선택 시에만 import
        from chatbot.generator import Generator

        app.state.generator = Generator()
    else:
        raise ValueError(f"unknown CHATBOT_BACKEND: {backend}")
    yield
    for name in ("generator", "encoder", "collection"):
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

    generator = request.app.state.generator

    started_at = perf_counter()
    articles = await retrieve_rag_articles(request, payload.question)
    response = await asyncio.to_thread(
        answer_question,
        generator=generator,
        question=payload.question,
        articles=articles,
    )
    generation_seconds = perf_counter() - started_at

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

    generator = request.app.state.generator
    articles = await retrieve_rag_articles(request, payload.question)

    return StreamingResponse(
        stream_answer_question(
            generator=generator,
            question=payload.question,
            articles=articles,
        ),
        media_type="text/plain; charset=utf-8",
    )
