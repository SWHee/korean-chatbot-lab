"""테스트 공통 환경 설정"""

import pytest


@pytest.fixture(autouse=True)
def disable_langsmith_tracing(monkeypatch) -> None:
    """단위 테스트 중 LangSmith 업로드 방지"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
