"""환경 변수로 생성 backend 선택"""

import os

from chatbot.generation.anthropic import AnthropicGenerator
from chatbot.generation.ollama import OllamaGenerator


DEFAULT_BACKEND = "anthropic"
BACKEND_ENV = "CHATBOT_BACKEND"


def create_generator():
    """현재 설정에 맞는 생성기 준비"""
    backend = os.getenv(BACKEND_ENV, DEFAULT_BACKEND).strip().lower()

    if backend == "anthropic":
        return AnthropicGenerator()
    if backend == "ollama":
        return OllamaGenerator()
    raise ValueError(f"unknown {BACKEND_ENV}: {backend}")
