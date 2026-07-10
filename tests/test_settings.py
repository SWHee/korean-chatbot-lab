"""로컬 환경 변수 설정 테스트"""

import os

from chatbot.settings import DEFAULT_LANGSMITH_PROJECT, load_local_env


def test_load_local_env_reads_langsmith_key_and_sets_project(
    tmp_path, monkeypatch
) -> None:
    """API key만 채운 .env로 LangSmith 기본 project 준비"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LANGSMITH_TRACING=true\n"
        "LANGSMITH_API_KEY=lsv2_test_key\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)

    load_local_env(env_file)

    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "lsv2_test_key"
    assert os.environ["LANGSMITH_PROJECT"] == DEFAULT_LANGSMITH_PROJECT
