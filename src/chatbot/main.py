"""FastAPI 금융 상담 application 진입점"""

from fastapi import FastAPI

from chatbot.api.lifecycle import lifespan
from chatbot.api.routes import router

app = FastAPI(
    title="Korean Chatbot",
    lifespan=lifespan,
)
app.include_router(router)
