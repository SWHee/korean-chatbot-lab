from fastapi import FastAPI

from chatbot.api.routes import router


def test_router_exposes_active_and_rag_diagnostic_paths() -> None:
    """현재 서비스와 법령 진단 endpoint 공개"""
    app = FastAPI()
    app.include_router(router)

    paths = app.openapi()["paths"]

    assert set(paths) == {"/ask-rag", "/ask-agent", "/ask-agent/stream"}
