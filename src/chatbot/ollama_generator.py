"""Ollama HTTP API 기반 로컬 생성기"""

import json
import os
from collections.abc import Generator, Iterator
from typing import TypeVar

import httpx
from pydantic import BaseModel
from pydantic_core import from_json


MODEL_ID = "qwen3:4b-instruct-2507-q4_K_M"
BASE_URL = "http://localhost:11434"
MAX_NEW_TOKENS = 1024  # Ollama backend 생성 길이 상한
TIMEOUT_SECONDS = 60.0
StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)


class OllamaGenerator:
    """Ollama 서버의 양자화 Qwen3 모델로 답변 생성"""

    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", BASE_URL)

    def _chat_payload(self, prompt: str, stream: bool) -> dict:
        """Ollama chat API 요청 본문 구성"""
        return {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "options": {"num_predict": MAX_NEW_TOKENS},
        }

    def generate(self, prompt: str) -> str:
        """사용자 문장을 Ollama chat API에 전달해 답변 문자열 반환"""
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=self._chat_payload(prompt, stream=False),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        response_model: type[StructuredResponse],
    ) -> StructuredResponse:
        """역할별 메시지와 JSON schema로 검증된 응답 생성"""
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=self._structured_chat_payload(
                messages=messages,
                response_model=response_model,
                stream=False,
            ),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response_model.model_validate_json(
            response.json()["message"]["content"]
        )

    def stream_structured(
        self,
        *,
        messages: list[dict[str, str]],
        response_model: type[StructuredResponse],
    ) -> Generator[dict[str, object], None, StructuredResponse]:
        """부분 JSON 상태 전달과 완성된 구조화 응답 검증"""
        content = ""
        last_partial = None
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=self._structured_chat_payload(
                messages=messages,
                response_model=response_model,
                stream=True,
            ),
            timeout=TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    raise RuntimeError(str(chunk["error"]))

                piece = chunk.get("message", {}).get("content", "")
                if not piece:
                    continue
                content += piece
                try:
                    partial = from_json(
                        content,
                        allow_partial="trailing-strings",
                    )
                except ValueError:
                    continue
                if isinstance(partial, dict) and partial != last_partial:
                    last_partial = partial
                    yield partial

        return response_model.model_validate_json(content)

    @staticmethod
    def _structured_chat_payload(
        *,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
        stream: bool,
    ) -> dict:
        """구조화 chat 요청 본문"""
        return {
            "model": MODEL_ID,
            "messages": messages,
            "format": response_model.model_json_schema(),
            "stream": stream,
            "options": {
                "num_predict": MAX_NEW_TOKENS,
                "temperature": 0,
            },
        }

    def stream(self, prompt: str) -> Iterator[str]:
        """모델이 생성하는 답변 조각을 순차 반환"""
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=self._chat_payload(prompt, stream=True),
            timeout=TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()

            # Ollama는 조각마다 JSON 한 줄을 전송
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if chunk.get("done"):
                    break
                yield chunk["message"]["content"]
