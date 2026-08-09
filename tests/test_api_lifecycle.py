import asyncio
from types import SimpleNamespace

import chatbot.api.lifecycle as lifecycle_module


def test_lifespan_loads_local_env_before_backend_selection(monkeypatch) -> None:
    """서버 시작 시 .env를 읽은 뒤 backend 준비"""
    calls = []
    generator = object()

    async def run_lifespan():
        state = SimpleNamespace()
        app = SimpleNamespace(state=state)
        async with lifecycle_module.lifespan(app):
            assert app.state.generator is generator

    monkeypatch.setattr(
        lifecycle_module,
        "load_local_env",
        lambda: calls.append("env"),
    )
    monkeypatch.setattr(
        lifecycle_module,
        "create_generator",
        lambda: calls.append("generator") or generator,
    )

    asyncio.run(run_lifespan())

    assert calls == ["env", "generator"]


def test_lifespan_shuts_down_enabled_langfeather(monkeypatch) -> None:
    """서버 종료 시 대기 중인 LangFeather 추적 전송"""
    shutdown_timeouts = []

    async def run_lifespan():
        state = SimpleNamespace()
        app = SimpleNamespace(state=state)
        async with lifecycle_module.lifespan(app):
            app.state.langfeather_sdk = SimpleNamespace(
                shutdown=lambda timeout: shutdown_timeouts.append(timeout) or True
            )

    monkeypatch.setattr(lifecycle_module, "load_local_env", lambda: None)
    monkeypatch.setattr(lifecycle_module, "create_generator", object)

    asyncio.run(run_lifespan())

    assert shutdown_timeouts == [2.0]
