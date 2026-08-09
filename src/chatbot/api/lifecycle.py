"""FastAPI 서버 시작·종료 수명주기"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatbot.generation import create_generator
from chatbot.observability.langfeather import shutdown_langfeather
from chatbot.settings import load_local_env

LANGFEATHER_SHUTDOWN_TIMEOUT_SECONDS = 2.0
APP_STATE_RESOURCE_NAMES = (
    "generator",
    "encoder",
    "collection",
    "rag_graph",
    "agent_graph",
    "agent_checkpointer",
    "langfeather_sdk",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 생성기 준비와 종료 시 공유 자원 해제"""
    load_local_env()
    app.state.generator = create_generator()
    try:
        yield
    finally:
        await asyncio.to_thread(
            shutdown_langfeather,
            getattr(app.state, "langfeather_sdk", None),
            timeout_seconds=LANGFEATHER_SHUTDOWN_TIMEOUT_SECONDS,
        )
        agent_checkpointer = getattr(app.state, "agent_checkpointer", None)
        if agent_checkpointer:
            agent_checkpointer.conn.close()
        for name in APP_STATE_RESOURCE_NAMES:
            if hasattr(app.state, name):
                delattr(app.state, name)
