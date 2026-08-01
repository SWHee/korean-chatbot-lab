"""Anthropic 생성기 요청과 스트리밍 계약 검증"""

from types import SimpleNamespace
from typing import Literal

import pytest
from pydantic import BaseModel

import chatbot.anthropic_generator as anthropic_module


class ExampleResponse(BaseModel):
    """테스트용 구조화 응답"""

    status: Literal["ok"]
    answer: str


class FakeStream:
    """Anthropic text stream 대역"""

    def __init__(self, pieces: list[str]) -> None:
        self.text_stream = iter(pieces)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        pass


class FakeMessages:
    """Anthropic messages resource 대역"""

    def __init__(self) -> None:
        self.requests = []
        self.stream_pieces = []
        self.parsed_output = None

    def create(self, **kwargs):
        self.requests.append(("create", kwargs))
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="일반 "),
                SimpleNamespace(type="text", text="답변"),
            ]
        )

    def parse(self, **kwargs):
        self.requests.append(("parse", kwargs))
        return SimpleNamespace(parsed_output=self.parsed_output)

    def stream(self, **kwargs):
        self.requests.append(("stream", kwargs))
        return FakeStream(self.stream_pieces)


def install_fake_client(monkeypatch) -> tuple[FakeMessages, dict]:
    """생성기 초기화 인자와 Messages 요청 수집"""
    messages = FakeMessages()
    client_options = {}

    def fake_anthropic(**kwargs):
        client_options.update(kwargs)
        return SimpleNamespace(messages=messages)

    monkeypatch.setattr(anthropic_module, "Anthropic", fake_anthropic)
    monkeypatch.setenv(anthropic_module.API_KEY_ENV, "test-api-key")
    return messages, client_options


def consume_structured_stream(stream):
    """부분 상태와 generator 반환값 수집"""
    partials = []
    while True:
        try:
            partials.append(next(stream))
        except StopIteration as completed:
            return partials, completed.value


def test_generate_and_stream_use_configured_model(monkeypatch) -> None:
    """환경 모델과 일반 생성 계약 사용"""
    messages, client_options = install_fake_client(monkeypatch)
    monkeypatch.setenv(anthropic_module.MODEL_ENV, "claude-test-model")
    monkeypatch.setenv(anthropic_module.TIMEOUT_ENV, "30")
    messages.stream_pieces = ["스트림 ", "답변"]

    generator = anthropic_module.AnthropicGenerator()

    assert generator.generate("질문") == "일반 답변"
    assert list(generator.stream("질문")) == ["스트림 ", "답변"]
    assert client_options == {"api_key": "test-api-key", "timeout": 30.0}
    assert messages.requests[0] == (
        "create",
        {
            "model": "claude-test-model",
            "max_tokens": anthropic_module.MAX_OUTPUT_TOKENS,
            "messages": [{"role": "user", "content": "질문"}],
        },
    )


def test_generate_structured_separates_system_message(monkeypatch) -> None:
    """system 지시 분리와 Pydantic output format 전달"""
    messages, _ = install_fake_client(monkeypatch)
    expected = ExampleResponse(status="ok", answer="검증된 답변")
    messages.parsed_output = expected

    result = anthropic_module.AnthropicGenerator().generate_structured(
        messages=[
            {"role": "system", "content": "법령 근거만 사용하세요."},
            {"role": "user", "content": "예금은 보호되나요?"},
        ],
        response_model=ExampleResponse,
    )

    assert result == expected
    method, request = messages.requests[0]
    assert method == "parse"
    assert request["system"] == "법령 근거만 사용하세요."
    assert request["messages"] == [
        {"role": "user", "content": "예금은 보호되나요?"}
    ]
    assert request["output_format"] is ExampleResponse
    assert request["temperature"] == 0


def test_stream_structured_yields_partial_and_validated_result(
    monkeypatch,
) -> None:
    """구조화 JSON 조각과 최종 Pydantic 검증"""
    messages, _ = install_fake_client(monkeypatch)
    messages.stream_pieces = [
        '{"status":"ok","answer":"검',
        "증된 ",
        '답변"}',
    ]

    partials, result = consume_structured_stream(
        anthropic_module.AnthropicGenerator().stream_structured(
            messages=[{"role": "user", "content": "질문"}],
            response_model=ExampleResponse,
        )
    )

    assert result == ExampleResponse(status="ok", answer="검증된 답변")
    assert [partial["answer"] for partial in partials if "answer" in partial] == [
        "검",
        "검증된 ",
        "검증된 답변",
    ]
    method, request = messages.requests[0]
    assert method == "stream"
    assert request["output_format"] is ExampleResponse
    assert request["temperature"] == 0


def test_generate_structured_rejects_missing_output(monkeypatch) -> None:
    """구조화 결과가 없는 Claude 응답 거부"""
    install_fake_client(monkeypatch)

    with pytest.raises(ValueError, match="no structured output"):
        anthropic_module.AnthropicGenerator().generate_structured(
            messages=[{"role": "user", "content": "질문"}],
            response_model=ExampleResponse,
        )
