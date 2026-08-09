from types import SimpleNamespace

import chatbot.observability.langfeather as langfeather_module


def test_configure_langfeather_returns_none_when_disabled(monkeypatch) -> None:
    """비활성 환경의 SDK 미사용"""
    monkeypatch.setenv("LANGFEATHER_ENABLED", "false")

    assert langfeather_module.configure_langfeather() is None


def test_configure_langfeather_uses_optional_endpoint(monkeypatch) -> None:
    """활성 환경의 SDK endpoint 설정"""
    configured_endpoints = []
    sdk = SimpleNamespace(
        configure=lambda endpoint: configured_endpoints.append(endpoint),
    )
    monkeypatch.setenv("LANGFEATHER_ENABLED", "true")
    monkeypatch.setenv("LANGFEATHER_ENDPOINT", "http://127.0.0.1:4319")
    monkeypatch.setattr(langfeather_module, "load_langfeather", lambda: sdk)

    assert langfeather_module.configure_langfeather() is sdk
    assert configured_endpoints == ["http://127.0.0.1:4319"]


def test_wrap_runnable_keeps_original_when_sdk_is_none() -> None:
    """비활성 추적의 원본 Runnable 보존"""
    runnable = object()

    assert (
        langfeather_module.wrap_runnable(runnable, sdk=None, name="test")
        is runnable
    )


def test_wrap_runnable_delegates_to_sdk() -> None:
    """활성 추적의 Runnable 래핑"""
    runnable = object()
    traced_runnable = object()
    wrapped = []
    sdk = SimpleNamespace(
        wrap_runnable=lambda target, *, name: wrapped.append((target, name))
        or traced_runnable,
    )

    result = langfeather_module.wrap_runnable(
        runnable,
        sdk=sdk,
        name="korean-chatbot-agent",
    )

    assert result is traced_runnable
    assert wrapped == [(runnable, "korean-chatbot-agent")]


def test_shutdown_langfeather_skips_missing_sdk() -> None:
    """비활성 추적의 종료 처리 생략"""
    langfeather_module.shutdown_langfeather(None, timeout_seconds=2.0)
