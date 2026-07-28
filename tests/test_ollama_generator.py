"""Ollama HTTP 생성기 요청 형식 검증"""

import json
from typing import Literal

import pytest
from pydantic import BaseModel, ValidationError

import chatbot.ollama_generator as ollama_module


class ExampleResponse(BaseModel):
    """테스트용 구조화 응답"""

    status: Literal["ok"]
    answer: str


class FakeResponse:
    """httpx 응답의 최소 대역"""

    def __init__(self, content: str) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"message": {"content": self.content}}


class FakeStreamResponse:
    """Ollama NDJSON stream 응답 대역"""

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        pass

    def raise_for_status(self) -> None:
        pass

    def iter_lines(self):
        yield from self.lines


def consume_structured_stream(stream):
    """부분 상태와 generator 반환값 수집"""
    partials = []
    while True:
        try:
            partials.append(next(stream))
        except StopIteration as completed:
            return partials, completed.value


def test_generate_structured_sends_roles_and_json_schema(monkeypatch) -> None:
    """역할별 메시지와 Pydantic schema를 Ollama에 전달"""
    request = {}

    def fake_post(url, *, json, timeout):
        request.update({"url": url, "json": json, "timeout": timeout})
        return FakeResponse('{"status":"ok","answer":"검증된 답변"}')

    monkeypatch.setattr(ollama_module.httpx, "post", fake_post)
    messages = [
        {"role": "system", "content": "법령 근거만 사용하세요."},
        {"role": "user", "content": "예금은 보호되나요?"},
    ]

    result = ollama_module.OllamaGenerator().generate_structured(
        messages=messages,
        response_model=ExampleResponse,
    )

    assert result == ExampleResponse(status="ok", answer="검증된 답변")
    assert request["url"] == f"{ollama_module.BASE_URL}/api/chat"
    assert request["timeout"] == ollama_module.TIMEOUT_SECONDS
    assert request["json"]["messages"] == messages
    assert request["json"]["format"] == ExampleResponse.model_json_schema()
    assert request["json"]["stream"] is False
    assert request["json"]["options"] == {
        "num_predict": ollama_module.MAX_NEW_TOKENS,
        "temperature": 0,
    }


def test_stream_structured_yields_partial_json_and_validated_result(
    monkeypatch,
) -> None:
    """구조화 JSON 조각 누적과 최종 Pydantic 검증"""
    request = {}
    pieces = ['{"status":"ok","answer":"검', "증된 ", '답변"', "}"]
    lines = [
        json.dumps(
            {"message": {"content": piece}, "done": index == len(pieces) - 1}
        )
        for index, piece in enumerate(pieces)
    ]

    def fake_stream(method, url, *, json, timeout):
        request.update(
            {
                "method": method,
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeStreamResponse(lines)

    monkeypatch.setattr(ollama_module.httpx, "stream", fake_stream)

    partials, result = consume_structured_stream(
        ollama_module.OllamaGenerator().stream_structured(
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
    assert request["method"] == "POST"
    assert request["url"] == f"{ollama_module.BASE_URL}/api/chat"
    assert request["json"]["stream"] is True
    assert request["json"]["format"] == ExampleResponse.model_json_schema()
    assert request["timeout"] == ollama_module.TIMEOUT_SECONDS


def test_generator_reads_ollama_base_url(monkeypatch) -> None:
    """환경 변수의 Ollama 주소 사용"""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")

    generator = ollama_module.OllamaGenerator()

    assert generator.base_url == "http://ollama:11434"


def test_generate_structured_rejects_invalid_response(monkeypatch) -> None:
    """schema를 만족하지 않는 모델 응답 거부"""
    monkeypatch.setattr(
        ollama_module.httpx,
        "post",
        lambda *args, **kwargs: FakeResponse('{"status":"unknown"}'),
    )

    with pytest.raises(ValidationError):
        ollama_module.OllamaGenerator().generate_structured(
            messages=[{"role": "user", "content": "질문"}],
            response_model=ExampleResponse,
        )
