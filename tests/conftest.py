"""테스트 공통 환경 설정"""

import pytest


@pytest.fixture(autouse=True)
def disable_langsmith_tracing(monkeypatch) -> None:
    """단위 테스트 중 외부 추적 전송 방지"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGFEATHER_ENABLED", "false")
