"""Anthropic Messages API 기반 생성기"""

import os
from collections.abc import Generator, Iterator
from typing import TypeVar

from anthropic import Anthropic
from pydantic import BaseModel
from pydantic_core import from_json


DEFAULT_MODEL_ID = "claude-haiku-4-5-20251001"
API_KEY_ENV = "ANTHROPIC_API_KEY"
MODEL_ENV = "ANTHROPIC_MODEL"
TIMEOUT_ENV = "ANTHROPIC_TIMEOUT_SECONDS"
MAX_OUTPUT_TOKENS = 1024
TIMEOUT_SECONDS = 60.0
StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)


class AnthropicGenerator:
    """Claude Haiku API로 답변 생성"""

    def __init__(self) -> None:
        self.model = os.getenv(MODEL_ENV, DEFAULT_MODEL_ID)
        self.timeout_seconds = float(
            os.getenv(TIMEOUT_ENV, str(TIMEOUT_SECONDS))
        )
        self.client = Anthropic(
            api_key=os.environ[API_KEY_ENV],
            timeout=self.timeout_seconds,
        )

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """system 지시와 Claude 대화 메시지 분리"""
        system_parts = []
        conversation = []

        for message in messages:
            role = message["role"]
            if role == "system":
                system_parts.append(message["content"])
            elif role in {"user", "assistant"}:
                conversation.append(message)
            else:
                raise ValueError(f"unsupported Anthropic message role: {role}")

        if not conversation:
            raise ValueError("Anthropic messages require user or assistant content")

        return "\n\n".join(system_parts), conversation

    def _request_inputs(
        self,
        messages: list[dict[str, str]],
    ) -> dict[str, object]:
        """공통 Messages API 입력"""
        system, conversation = self._split_messages(messages)
        inputs: dict[str, object] = {
            "model": self.model,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "messages": conversation,
        }
        if system:
            inputs["system"] = system
        return inputs

    @staticmethod
    def _response_text(response) -> str:
        """Claude text block 결합"""
        return "".join(
            block.text
            for block in response.content
            if block.type == "text"
        )

    def generate(self, prompt: str) -> str:
        """사용자 문장의 일반 응답 생성"""
        response = self.client.messages.create(
            **self._request_inputs(
                [{"role": "user", "content": prompt}]
            )
        )
        return self._response_text(response)

    def stream(self, prompt: str) -> Iterator[str]:
        """일반 응답 텍스트 조각 전달"""
        with self.client.messages.stream(
            **self._request_inputs(
                [{"role": "user", "content": prompt}]
            )
        ) as stream:
            yield from stream.text_stream

    def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        response_model: type[StructuredResponse],
    ) -> StructuredResponse:
        """Pydantic schema를 만족하는 응답 생성"""
        response = self.client.messages.parse(
            **self._request_inputs(messages),
            output_format=response_model,
            temperature=0,
        )
        if response.parsed_output is None:
            raise ValueError("Anthropic response has no structured output")
        return response.parsed_output

    def stream_structured(
        self,
        *,
        messages: list[dict[str, str]],
        response_model: type[StructuredResponse],
    ) -> Generator[dict[str, object], None, StructuredResponse]:
        """부분 JSON 상태 전달과 완성된 구조화 응답 검증"""
        content = ""
        last_partial = None

        with self.client.messages.stream(
            **self._request_inputs(messages),
            output_format=response_model,
            temperature=0,
        ) as stream:
            for piece in stream.text_stream:
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
