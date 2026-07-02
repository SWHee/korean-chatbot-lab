import asyncio
import logging
from types import SimpleNamespace

import chatbot.main as main_module


class FakeGenerator:
    """모델 적재 없이 고정 답변 반환"""

    def generate(self, prompt: str) -> str:
        return "테스트 답변"


def create_request() -> SimpleNamespace:
    """테스트용 Generator를 담은 요청 생성"""
    generator = FakeGenerator()
    state = SimpleNamespace(generator=generator)
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def test_chat_returns_generation_seconds(monkeypatch) -> None:
    """응답에 답변 생성 시간 포함"""
    times = iter([10.0, 12.5])
    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))

    response = asyncio.run(
        main_module.chat(
            main_module.ChatRequest(prompt="질문"),
            create_request(),
        )
    )

    assert response.response == "테스트 답변"
    assert response.generation_seconds == 2.5


def test_chat_logs_generation_seconds(monkeypatch, caplog) -> None:
    """서버 로그에 답변 생성 시간 기록"""
    times = iter([10.0, 12.5])
    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        asyncio.run(
            main_module.chat(
                main_module.ChatRequest(prompt="질문"),
                create_request(),
            )
        )

    assert "generation_seconds=2.500" in caplog.text
