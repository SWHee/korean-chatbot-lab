"""생성 backend 선택 테스트"""

import pytest

import chatbot.generation.factory as backend_module


def test_create_generator_selects_anthropic_by_default(monkeypatch) -> None:
    """기본 backend로 Anthropic 생성기 선택"""
    generator = object()
    monkeypatch.delenv("CHATBOT_BACKEND", raising=False)
    monkeypatch.setattr(
        backend_module,
        "AnthropicGenerator",
        lambda: generator,
    )

    assert backend_module.create_generator() is generator


def test_create_generator_keeps_ollama_as_manual_option(monkeypatch) -> None:
    """환경 변수로 기존 Ollama 생성기 선택"""
    generator = object()
    monkeypatch.setenv("CHATBOT_BACKEND", "ollama")
    monkeypatch.setattr(
        backend_module,
        "OllamaGenerator",
        lambda: generator,
    )

    assert backend_module.create_generator() is generator


def test_create_generator_rejects_unknown_backend(monkeypatch) -> None:
    """지원하지 않는 backend 설정 거부"""
    monkeypatch.setenv("CHATBOT_BACKEND", "unknown")

    with pytest.raises(ValueError, match="unknown CHATBOT_BACKEND"):
        backend_module.create_generator()
