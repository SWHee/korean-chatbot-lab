"""FastAPI 챗봇 API와 생성 backend 수명주기"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from chatbot.ollama_generator import OllamaGenerator


logger = logging.getLogger("uvicorn.error")


class ChatRequest(BaseModel):
    """챗봇에 전달할 사용자 질문 검증"""

    prompt: str = Field(min_length=1)


class ChatResponse(BaseModel):
    """챗봇이 생성한 답변 형식 정의"""

    response: str
    generation_seconds: float


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 선택한 backend의 생성기를 준비하고 종료 시 해제"""
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
    del app.state.generator


app = FastAPI(
    title="Korean Chatbot",
    lifespan=lifespan,
)


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """사용자 질문을 로컬 모델에 전달해 답변 반환"""
    generator = request.app.state.generator

    # 동기식 모델 추론을 별도 thread에서 실행
    started_at = perf_counter()
    response = await asyncio.to_thread(generator.generate, payload.prompt)
    generation_seconds = perf_counter() - started_at
    logger.info("generation_seconds=%.3f", generation_seconds)

    return ChatResponse(
        response=response,
        generation_seconds=generation_seconds,
    )


@app.post("/chat/stream", response_class=StreamingResponse)
async def chat_stream(payload: ChatRequest, request: Request,) -> StreamingResponse:
    """사용자 질문에 대한 답변을 조각별로 전송"""
    generator = request.app.state.generator
    return StreamingResponse(
        generator.stream(payload.prompt),
        media_type="text/plain; charset=utf-8",
    )
