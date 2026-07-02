import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from chatbot.generator import Generator


PROMPT = "AI 서비스 개발자가 되기 위한 첫 단계는 무엇인가요?"
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
    """서버 시작 시 모델을 한 번 적재하고 종료 시 해제"""
    app.state.generator = Generator()
    yield
    del app.state.generator


app = FastAPI(
    title="Korean Chatbot",
    lifespan=lifespan,
)


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """사용자 질문을 로컬 모델에 전달해 답변 반환"""
    generator: Generator = request.app.state.generator

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
    generator: Generator = request.app.state.generator
    return StreamingResponse(
        generator.stream(payload.prompt),
        media_type="text/plain; charset=utf-8",
    )


def main() -> None:
    """로컬 생성기를 실행해 답변 출력"""
    generator = Generator()
    response = generator.generate(PROMPT)
    print(f"모델 답변:\n{response}")


if __name__ == "__main__":
    main()
