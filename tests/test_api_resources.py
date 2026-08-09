from types import SimpleNamespace

import chatbot.api.resources as resources_module


class FakeGenerator:
    """모델 적재 없는 테스트 생성기"""


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

    monkeypatch.setattr(resources_module, "load_encoder", lambda: encoder)
    monkeypatch.setattr(resources_module, "open_collection", lambda: collection)
    monkeypatch.setattr(resources_module, "create_rag_graph", fake_create_rag_graph)
    monkeypatch.setattr(resources_module, "configure_langfeather", lambda: None)
    monkeypatch.setattr(
        resources_module,
        "wrap_runnable",
        lambda runnable, **kwargs: runnable,
    )

    resources_module.prepare_rag_resources(app)

    assert app.state.encoder is encoder
    assert app.state.collection is collection
    assert app.state.rag_graph is rag_graph
    assert graph_resources == {
        "generator": app.state.generator,
        "encoder": encoder,
        "collection": collection,
        "top_k": 5,
    }
    assert app.state.langfeather_sdk is None


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
            langfeather_sdk=None,
        )
    )
    captured = {}

    monkeypatch.setattr(resources_module, "prepare_rag_resources", lambda app: None)
    monkeypatch.setattr(
        resources_module,
        "wrap_runnable",
        lambda runnable, **kwargs: runnable,
    )
    monkeypatch.setattr(
        resources_module,
        "create_tool_calling_model",
        lambda: tool_model,
    )
    monkeypatch.setattr(resources_module, "create_agent_tools", lambda **kwargs: tools)
    monkeypatch.setattr(
        resources_module,
        "create_turn_analyzer",
        lambda **kwargs: turn_analyzer,
    )
    monkeypatch.setattr(
        resources_module,
        "create_sqlite_checkpointer",
        lambda: checkpointer,
    )

    def fake_create_multi_turn_agent_graph(**kwargs):
        captured.update(kwargs)
        return agent_graph

    monkeypatch.setattr(
        resources_module,
        "create_multi_turn_agent_graph",
        fake_create_multi_turn_agent_graph,
    )

    resources_module.prepare_agent_resources(app)

    assert app.state.agent_graph is agent_graph
    assert app.state.agent_checkpointer is checkpointer
    assert captured == {
        "model": tool_model,
        "tools": tools,
        "analyze_turn": turn_analyzer,
        "checkpointer": checkpointer,
    }
