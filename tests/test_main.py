import asyncio
import logging
from types import SimpleNamespace

import chatbot.main as main_module


class FakeGenerator:
    """모델 적재 없이 고정 답변 반환"""

    def generate(self, prompt: str) -> str:
        return "테스트 답변"

    def stream(self, prompt: str):
        yield "테스트 "
        yield "스트림"


def create_request() -> SimpleNamespace:
    """테스트용 Generator를 담은 요청 생성"""
    generator = FakeGenerator()
    state = SimpleNamespace(generator=generator)
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def create_rag_request() -> SimpleNamespace:
    """테스트용 RAG 자원을 담은 요청 생성"""
    state = SimpleNamespace(
        generator=FakeGenerator(),
        encoder=object(),
        collection=object(),
    )
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def test_lifespan_loads_local_env_before_backend_selection(monkeypatch) -> None:
    """서버 시작 시 .env를 읽은 뒤 backend 준비"""
    calls = []

    class FakeOllamaGenerator:
        pass

    async def run_lifespan():
        state = SimpleNamespace()
        app = SimpleNamespace(state=state)
        async with main_module.lifespan(app):
            assert isinstance(app.state.generator, FakeOllamaGenerator)

    monkeypatch.setenv("CHATBOT_BACKEND", "ollama")
    monkeypatch.setattr(main_module, "load_local_env", lambda: calls.append("env"))
    monkeypatch.setattr(main_module, "OllamaGenerator", FakeOllamaGenerator)

    asyncio.run(run_lifespan())

    assert calls == ["env"]


def test_chat_returns_generation_seconds(monkeypatch) -> None:
    """응답에 답변 생성 시간 포함"""
    times = iter([10.0, 12.5])
    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))

    response = asyncio.run(
        main_module.chat(
            main_module.ChatRequest(prompt="질문"),
            create_request(),
        )
    )

    assert response.response == "테스트 답변"
    assert response.generation_seconds == 2.5


def test_chat_logs_generation_seconds(monkeypatch, caplog) -> None:
    """서버 로그에 답변 생성 시간 기록"""
    times = iter([10.0, 12.5])
    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        asyncio.run(
            main_module.chat(
                main_module.ChatRequest(prompt="질문"),
                create_request(),
            )
        )

    assert "generation_seconds=2.500" in caplog.text


def test_ask_rag_route_exists() -> None:
    """Swagger에 RAG 질문 endpoint 노출"""
    assert "/ask-rag" in main_module.app.openapi()["paths"]


def test_retrieve_rag_articles_uses_shared_top_k(monkeypatch) -> None:
    """두 RAG endpoint가 공유할 법령 검색 준비"""
    request = create_rag_request()
    articles = [{"article_no": "제18조"}]
    calls = {}

    def fake_retrieve_articles(encoder, collection, question, top_k):
        calls.update(
            encoder=encoder,
            collection=collection,
            question=question,
            top_k=top_k,
        )
        return articles

    monkeypatch.setattr(main_module, "retrieve_articles", fake_retrieve_articles)

    result = asyncio.run(
        main_module.retrieve_rag_articles(
            request,
            "예금은 얼마까지 보호되나요?",
        )
    )

    assert result == articles
    assert calls == {
        "encoder": request.app.state.encoder,
        "collection": request.app.state.collection,
        "question": "예금은 얼마까지 보호되나요?",
        "top_k": 5,
    }


def test_ask_rag_returns_answer_sources_and_generation_seconds(monkeypatch) -> None:
    """RAG 검색 근거와 답변 반환"""
    times = iter([20.0, 23.0])
    retrieved_articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "similarity": 0.82,
            "text": "보험금 한도는 1억원",
        }
    ]

    def fake_retrieve_articles(encoder, collection, question, top_k):
        assert question == "예금은 얼마까지 보호되나요?"
        assert top_k == 5
        return retrieved_articles

    def fake_answer_question(generator, question, articles):
        assert question == "예금은 얼마까지 보호되나요?"
        assert articles == retrieved_articles
        return "예금은 1인당 1억원까지 보호됩니다."

    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))
    monkeypatch.setattr(main_module, "retrieve_articles", fake_retrieve_articles)
    monkeypatch.setattr(main_module, "answer_question", fake_answer_question)

    response = asyncio.run(
        main_module.ask_rag(
            main_module.RagRequest(question="예금은 얼마까지 보호되나요?"),
            create_rag_request(),
        )
    )

    assert response.response == "예금은 1인당 1억원까지 보호됩니다."
    assert response.generation_seconds == 3.0
    assert response.sources[0].law_name == "예금자보호법 시행령"
    assert response.sources[0].article_no == "제18조"


def test_ask_rag_stream_route_exists() -> None:
    """Swagger에 RAG 스트리밍 endpoint 노출"""
    assert "/ask-rag/stream" in main_module.app.openapi()["paths"]


def test_ask_rag_stream_returns_plain_text_tokens(monkeypatch) -> None:
    """RAG 답변 조각을 순수 텍스트로 전송"""
    retrieved_articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "similarity": 0.82,
            "text": "보험금 한도는 1억원",
        }
    ]

    def fake_retrieve_articles(encoder, collection, question, top_k):
        return retrieved_articles

    def fake_stream_answer_question(generator, question, articles):
        assert question == "예금은 얼마까지 보호되나요?"
        assert articles == retrieved_articles
        yield "예금은 "
        yield "1억원까지 보호됩니다."

    async def collect_body():
        response = await main_module.ask_rag_stream(
            main_module.RagRequest(question="예금은 얼마까지 보호되나요?"),
            create_rag_request(),
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        return response, "".join(chunks)

    monkeypatch.setattr(main_module, "retrieve_articles", fake_retrieve_articles)
    monkeypatch.setattr(
        main_module, "stream_answer_question", fake_stream_answer_question
    )

    response, body = asyncio.run(collect_body())

    assert response.media_type == "text/plain; charset=utf-8"
    assert body == "예금은 1억원까지 보호됩니다."
