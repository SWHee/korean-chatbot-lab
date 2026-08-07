import asyncio
import json
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

import chatbot.main as main_module


class FakeGenerator:
    """모델 적재 없이 고정 답변 반환"""

    def generate(self, prompt: str) -> str:
        return "테스트 답변"

    def stream(self, prompt: str):
        yield "테스트 "
        yield "스트림"


def create_rag_request() -> SimpleNamespace:
    """테스트용 RAG 자원을 담은 요청 생성"""
    state = SimpleNamespace(
        generator=FakeGenerator(),
        encoder=object(),
        collection=object(),
    )
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def test_prepare_rag_resources_creates_graph(monkeypatch) -> None:
    """RAG 자원을 기존 Generator와 Graph에 연결"""
    encoder = object()
    collection = object()
    rag_graph = object()
    app = SimpleNamespace(state=SimpleNamespace(generator=FakeGenerator()))
    graph_resources = {}

    def fake_create_rag_graph(**resources):
        graph_resources.update(resources)
        return rag_graph

    monkeypatch.setattr(main_module, "load_encoder", lambda: encoder)
    monkeypatch.setattr(main_module, "open_collection", lambda: collection)
    monkeypatch.setattr(main_module, "create_rag_graph", fake_create_rag_graph)
    monkeypatch.delenv("LANGFEATHER_ENABLED", raising=False)

    main_module.prepare_rag_resources(app)

    assert app.state.encoder is encoder
    assert app.state.collection is collection
    assert app.state.rag_graph is rag_graph
    assert graph_resources == {
        "generator": app.state.generator,
        "encoder": encoder,
        "collection": collection,
        "top_k": 5,
    }
    assert app.state.langfeather_enabled is False


def test_prepare_rag_resources_wraps_graph_when_langfeather_enabled(
    monkeypatch,
) -> None:
    """환경 변수로 선택한 LangFeather 그래프 추적 연결"""
    rag_graph = object()
    traced_graph = object()
    app = SimpleNamespace(
        state=SimpleNamespace(
            generator=FakeGenerator(),
            encoder=object(),
            collection=object(),
        )
    )
    configured_endpoints = []
    wrapped_graphs = []
    langfeather_sdk = SimpleNamespace()

    monkeypatch.setenv("LANGFEATHER_ENABLED", "true")
    monkeypatch.setenv("LANGFEATHER_ENDPOINT", "http://127.0.0.1:4319")
    monkeypatch.setattr(
        main_module,
        "create_rag_graph",
        lambda **resources: rag_graph,
    )
    monkeypatch.setattr(
        main_module,
        "load_langfeather",
        lambda: langfeather_sdk,
    )
    langfeather_sdk.configure = lambda endpoint: configured_endpoints.append(endpoint)

    def fake_wrap_runnable(runnable, *, name):
        wrapped_graphs.append((runnable, name))
        return traced_graph

    langfeather_sdk.wrap_runnable = fake_wrap_runnable

    main_module.prepare_rag_resources(app)

    assert app.state.langfeather_enabled is True
    assert app.state.langfeather_sdk is langfeather_sdk
    assert app.state.rag_graph is traced_graph
    assert configured_endpoints == ["http://127.0.0.1:4319"]
    assert wrapped_graphs == [(rag_graph, "korean-chatbot-rag")]


def test_lifespan_loads_local_env_before_backend_selection(monkeypatch) -> None:
    """서버 시작 시 .env를 읽은 뒤 backend 준비"""
    calls = []
    generator = object()

    async def run_lifespan():
        state = SimpleNamespace()
        app = SimpleNamespace(state=state)
        async with main_module.lifespan(app):
            assert app.state.generator is generator

    monkeypatch.setattr(main_module, "load_local_env", lambda: calls.append("env"))
    monkeypatch.setattr(
        main_module,
        "create_generator",
        lambda: calls.append("generator") or generator,
    )

    asyncio.run(run_lifespan())

    assert calls == ["env", "generator"]


def test_lifespan_shuts_down_enabled_langfeather(monkeypatch) -> None:
    """서버 종료 시 대기 중인 LangFeather 추적 전송"""
    shutdown_timeouts = []

    async def run_lifespan():
        state = SimpleNamespace()
        app = SimpleNamespace(state=state)
        async with main_module.lifespan(app):
            app.state.langfeather_enabled = True
            app.state.langfeather_sdk = SimpleNamespace(
                shutdown=lambda timeout: shutdown_timeouts.append(timeout) or True
            )

    monkeypatch.setattr(main_module, "load_local_env", lambda: None)
    monkeypatch.setattr(main_module, "create_generator", object)

    asyncio.run(run_lifespan())

    assert shutdown_timeouts == [2.0]


def test_ask_rag_route_exists() -> None:
    """Swagger에 RAG 질문 endpoint 노출"""
    assert "/ask-rag" in main_module.app.openapi()["paths"]


def test_ask_rag_returns_answer_sources_and_generation_seconds(monkeypatch) -> None:
    """RAG Graph 결과를 답변과 검색 근거로 반환"""
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

    class FakeRagGraph:
        def invoke(self, input: dict) -> dict:
            assert input == {"question": "예금은 얼마까지 보호되나요?"}
            return {
                "question": input["question"],
                "articles": retrieved_articles,
                "answer": "예금은 1인당 1억원까지 보호됩니다.",
            }

    request = create_rag_request()
    request.app.state.rag_graph = FakeRagGraph()
    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))

    response = asyncio.run(
        main_module.ask_rag(
            main_module.RagRequest(question="예금은 얼마까지 보호되나요?"),
            request,
        )
    )

    assert response.response == "예금은 1인당 1억원까지 보호됩니다."
    assert response.generation_seconds == 3.0
    assert response.sources[0].law_name == "예금자보호법 시행령"
    assert response.sources[0].article_no == "제18조"


def test_ask_rag_stream_route_exists() -> None:
    """Swagger에 RAG 스트리밍 endpoint 노출"""
    assert "/ask-rag/stream" in main_module.app.openapi()["paths"]


def test_ask_rag_stream_returns_plain_text_tokens() -> None:
    """RAG Graph의 custom stream을 순수 텍스트로 전송"""

    class FakeRagGraph:
        def stream(self, input: dict, stream_mode: str):
            assert input == {
                "question": "예금은 얼마까지 보호되나요?",
                "streaming": True,
            }
            assert stream_mode == "custom"
            yield "예금은 "
            yield "1억원까지 보호됩니다."

    async def collect_body():
        request = create_rag_request()
        request.app.state.rag_graph = FakeRagGraph()
        response = await main_module.ask_rag_stream(
            main_module.RagRequest(question="예금은 얼마까지 보호되나요?"),
            request,
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        return response, "".join(chunks)

    response, body = asyncio.run(collect_body())

    assert response.media_type == "text/plain; charset=utf-8"
    assert body == "예금은 1억원까지 보호됩니다."


def test_prepare_workflow_resources_creates_graph(monkeypatch) -> None:
    """공유 RAG 자원으로 Routed Workflow Graph 준비"""
    routed_workflow_graph = object()
    app = SimpleNamespace(
        state=SimpleNamespace(
            generator=FakeGenerator(),
            encoder=object(),
            collection=object(),
            langfeather_enabled=False,
        )
    )
    graph_resources = {}

    monkeypatch.setattr(
        main_module,
        "prepare_rag_resources",
        lambda app: None,
    )

    def fake_create_routed_workflow_graph(**resources):
        graph_resources.update(resources)
        return routed_workflow_graph

    monkeypatch.setattr(
        main_module,
        "create_routed_workflow_graph",
        fake_create_routed_workflow_graph,
    )

    main_module.prepare_workflow_resources(app)

    assert app.state.routed_workflow_graph is routed_workflow_graph
    assert graph_resources == {
        "generator": app.state.generator,
        "encoder": app.state.encoder,
        "collection": app.state.collection,
        "top_k": 5,
    }


def test_ask_workflow_route_exists() -> None:
    """Swagger에 Routed Workflow endpoint 노출"""
    assert "/ask-workflow" in main_module.app.openapi()["paths"]


def test_ask_workflow_returns_mixed_result(monkeypatch) -> None:
    """혼합 답변과 route·상태·근거·상품·실행 시간 반환"""
    times = iter([30.0, 32.5])

    class FakeWorkflowGraph:
        def invoke(self, input: dict) -> dict:
            assert input == {
                "question": "12개월 정기예금과 예금자보호를 알려주세요."
            }
            return {
                "question": input["question"],
                "route": "mixed",
                "answer": "법령 안내와 상품 비교 결과입니다.",
                "law_status": "ok",
                "product_status": "ok",
                "articles": [
                    {
                        "law_name": "예금자보호법",
                        "article_no": "제32조",
                        "effective_date": "20260102",
                        "similarity": 0.88,
                        "text": "보험금 지급 기준",
                    }
                ],
                "products": [
                    {
                        "disclosure_month": "202607",
                        "company_code": "001",
                        "product_code": "DEPOSIT-001",
                        "company_name": "테스트은행",
                        "product_name": "테스트예금",
                        "term_months": 12,
                        "base_interest_rate": 3.1,
                        "max_interest_rate": 3.5,
                    }
                ],
            }

    request = create_rag_request()
    request.app.state.routed_workflow_graph = FakeWorkflowGraph()
    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))

    response = asyncio.run(
        main_module.ask_workflow(
            main_module.WorkflowRequest(
                question="12개월 정기예금과 예금자보호를 알려주세요."
            ),
            request,
        )
    )

    assert response.answer == "법령 안내와 상품 비교 결과입니다."
    assert response.route == "mixed"
    assert response.law_status == "ok"
    assert response.product_status == "ok"
    assert response.partial_failure is False
    assert response.execution_seconds == 2.5
    assert response.sources[0].law_name == "예금자보호법"
    assert response.products[0].product_name == "테스트예금"


def test_ask_workflow_marks_mixed_partial_failure(monkeypatch) -> None:
    """혼합 경로 한쪽 오류를 부분 실패로 표시"""
    class FakeWorkflowGraph:
        def invoke(self, input: dict) -> dict:
            return {
                "question": input["question"],
                "route": "mixed",
                "answer": "법령은 안내했지만 상품 정보는 불러오지 못했어요.",
                "law_status": "ok",
                "product_status": "error",
                "articles": [],
                "products": [],
            }

    request = create_rag_request()
    request.app.state.routed_workflow_graph = FakeWorkflowGraph()

    response = asyncio.run(
        main_module.ask_workflow(
            main_module.WorkflowRequest(
                question="12개월 정기예금과 예금자보호를 알려주세요."
            ),
            request,
        )
    )

    assert response.route == "mixed"
    assert response.law_status == "ok"
    assert response.product_status == "error"
    assert response.partial_failure is True
    assert response.products == []


def test_prepare_agent_resources_creates_multi_turn_graph(monkeypatch) -> None:
    """공유 RAG 자원과 SQLite Checkpointer로 Agent Graph 준비"""
    agent_graph = object()
    tool_model = object()
    tools = [object()]
    turn_analyzer = object()
    checkpointer = object()
    app = SimpleNamespace(
        state=SimpleNamespace(
            generator=FakeGenerator(),
            encoder=object(),
            collection=object(),
            langfeather_enabled=False,
        )
    )
    captured = {}

    monkeypatch.setattr(main_module, "prepare_rag_resources", lambda app: None)
    monkeypatch.setattr(main_module, "create_tool_calling_model", lambda: tool_model)
    monkeypatch.setattr(main_module, "create_agent_tools", lambda **kwargs: tools)
    monkeypatch.setattr(
        main_module,
        "create_turn_analyzer",
        lambda **kwargs: turn_analyzer,
    )
    monkeypatch.setattr(
        main_module,
        "create_sqlite_checkpointer",
        lambda: checkpointer,
    )

    def fake_create_multi_turn_agent_graph(**kwargs):
        captured.update(kwargs)
        return agent_graph

    monkeypatch.setattr(
        main_module,
        "create_multi_turn_agent_graph",
        fake_create_multi_turn_agent_graph,
    )

    main_module.prepare_agent_resources(app)

    assert app.state.agent_graph is agent_graph
    assert app.state.agent_checkpointer is checkpointer
    assert captured == {
        "model": tool_model,
        "tools": tools,
        "analyze_turn": turn_analyzer,
        "checkpointer": checkpointer,
    }


def test_ask_agent_route_exists() -> None:
    """Swagger에 멀티턴 Agent endpoint 노출"""
    assert "/ask-agent" in main_module.app.openapi()["paths"]


def test_ask_agent_returns_thread_tools_sources_and_products(monkeypatch) -> None:
    """Agent Graph 상태를 API 응답 계약으로 변환"""
    times = iter([10.0, 12.0])

    class FakeAgentGraph:
        def invoke(self, *, input: dict, config: dict) -> dict:
            assert input == {
                "messages": [
                    HumanMessage(content="12개월 정기예금과 예금자보호를 알려주세요.")
                ],
                "streaming": False,
            }
            assert config == {"configurable": {"thread_id": "thread-1"}}
            return {
                "route": "ready",
                "product_preferences": {
                    "product_type": "deposit",
                    "term_months": 12,
                    "sort_by": "base_interest_rate",
                    "limit": 3,
                },
                "missing_fields": [],
                "messages": [
                    input["messages"][0],
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "search_law_articles",
                                "args": {"question": "예금자보호"},
                                "id": "law-1",
                                "type": "tool_call",
                            },
                            {
                                "name": "search_financial_products",
                                "args": {
                                    "product_type": "deposit",
                                    "term_months": 12,
                                    "sort_by": "base_interest_rate",
                                    "limit": 3,
                                },
                                "id": "product-1",
                                "type": "tool_call",
                            },
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps(
                            {
                                "status": "ok",
                                "articles": [
                                    {
                                        "source_id": "S1",
                                        "law_name": "예금자보호법",
                                        "article_no": "제32조",
                                        "effective_date": "20260102",
                                        "text": "보험금 기준",
                                    }
                                ],
                            }
                        ),
                        tool_call_id="law-1",
                        name="search_law_articles",
                    ),
                    ToolMessage(
                        content=json.dumps(
                            {
                                "status": "ok",
                                "products": [
                                    {
                                        "disclosure_month": "202608",
                                        "company_code": "001",
                                        "product_code": "DEP-001",
                                        "company_name": "테스트은행",
                                        "product_name": "테스트예금",
                                        "term_months": 12,
                                        "base_interest_rate": 3.1,
                                        "max_interest_rate": 3.5,
                                    }
                                ],
                            }
                        ),
                        tool_call_id="product-1",
                        name="search_financial_products",
                    ),
                    AIMessage(content="법령과 상품 후보를 함께 확인했어요."),
                ],
            }

    request = create_rag_request()
    request.app.state.agent_graph = FakeAgentGraph()
    monkeypatch.setattr(main_module, "perf_counter", lambda: next(times))

    response = asyncio.run(
        main_module.ask_agent(
            main_module.AgentRequest(
                thread_id="thread-1",
                message="12개월 정기예금과 예금자보호를 알려주세요.",
            ),
            request,
        )
    )

    assert response.thread_id == "thread-1"
    assert response.answer == "법령과 상품 후보를 함께 확인했어요."
    assert response.route == "ready"
    assert response.product_preferences["term_months"] == 12
    assert [tool.name for tool in response.tools] == [
        "search_law_articles",
        "search_financial_products",
    ]
    assert response.tools[0].status == "ok"
    assert response.sources[0].article_no == "제32조"
    assert response.products[0].product_name == "테스트예금"
    assert response.execution_seconds == 2.0


def test_agent_execution_details_preserves_saving_product_fields() -> None:
    """Agent Tool 결과의 적금 구분과 적립 방식 보존"""
    messages = [
        HumanMessage(content="12개월 적금 후보를 알려주세요."),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_financial_products",
                    "args": {"product_type": "saving", "term_months": 12},
                    "id": "saving-1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content=json.dumps(
                {
                    "status": "ok",
                    "products": [
                        {
                            "product_type": "saving",
                            "disclosure_month": "202607",
                            "company_code": "001",
                            "product_code": "SAVING-001",
                            "company_name": "테스트은행",
                            "product_name": "테스트적금",
                            "term_months": 12,
                            "base_interest_rate": 3.1,
                            "max_interest_rate": 3.5,
                            "reserve_type": "F",
                            "reserve_type_name": "자유적립식",
                        }
                    ],
                }
            ),
            tool_call_id="saving-1",
            name="search_financial_products",
        ),
    ]

    tools, sources, products = main_module._agent_execution_details(messages)

    assert tools[0].status == "ok"
    assert sources == []
    assert products[0].product_type == "saving"
    assert products[0].reserve_type_name == "자유적립식"


def test_ask_agent_returns_clarifying_question_without_tools() -> None:
    """조건이 부족한 첫 턴은 Tool 없이 다음 질문을 반환"""
    class FakeAgentGraph:
        def invoke(self, *, input: dict, config: dict) -> dict:
            return {
                "route": "clarify",
                "product_preferences": {
                    "product_type": None,
                    "term_months": None,
                    "sort_by": "base_interest_rate",
                    "limit": 3,
                },
                "missing_fields": ["product_type", "term_months"],
                "messages": [
                    input["messages"][0],
                    AIMessage(content="예금과 적금 중 어떤 상품을 찾으시나요?"),
                ],
            }

    request = create_rag_request()
    request.app.state.agent_graph = FakeAgentGraph()

    response = asyncio.run(
        main_module.ask_agent(
            main_module.AgentRequest(
                thread_id="thread-clarify",
                message="금융상품 추천해 주세요.",
            ),
            request,
        )
    )

    assert response.route == "clarify"
    assert response.tools == []
    assert response.missing_fields == ["product_type", "term_months"]
    assert "예금과 적금" in response.answer


def test_ask_agent_stream_returns_status_token_and_result_events() -> None:
    """Agent Graph custom stream을 SSE 이벤트로 전달"""
    class FakeAgentGraph:
        def stream(self, *, input: dict, config: dict, stream_mode: list[str]):
            assert input == {
                "messages": [HumanMessage(content="안녕하세요.")],
                "streaming": True,
            }
            assert config == {"configurable": {"thread_id": "thread-stream"}}
            assert stream_mode == ["custom", "values"]
            yield "custom", {"event": "status", "stage": "analyze"}
            yield "custom", {"event": "token", "text": "안녕"}
            yield "custom", {"event": "token", "text": "하세요"}
            yield "values", {
                "route": "ready",
                "product_preferences": {},
                "missing_fields": [],
                "messages": [
                    input["messages"][0],
                    AIMessage(
                        content=[
                            {"text": "안녕하세요", "type": "text", "index": 0}
                        ]
                    ),
                ],
            }

    async def collect_body():
        request = create_rag_request()
        request.app.state.agent_graph = FakeAgentGraph()
        response = await main_module.ask_agent_stream(
            main_module.AgentRequest(thread_id="thread-stream", message="안녕하세요."),
            request,
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        return response, "".join(chunks)

    response, body = asyncio.run(collect_body())

    assert response.media_type == "text/event-stream"
    assert 'event: status\ndata: {"stage": "analyze"}' in body
    assert 'event: token\ndata: {"text": "안녕"}' in body
    assert 'event: result\ndata: {"thread_id": "thread-stream"' in body
    assert '"answer": "안녕하세요"' in body
