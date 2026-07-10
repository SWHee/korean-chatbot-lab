"""로컬 실행 환경 변수 로드"""

import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_LANGSMITH_PROJECT = "korean-chatbot-rag-dev"


def load_local_env(env_path: str | Path = ".env") -> None:
    """로컬 .env를 읽고 LangSmith 기본 project 설정"""
    load_dotenv(env_path, override=False)
    os.environ.setdefault("LANGSMITH_PROJECT", DEFAULT_LANGSMITH_PROJECT)
