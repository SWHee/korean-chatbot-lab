"""FastAPI 요청에서 공유하는 RAG·Agent 자원 준비"""

from fastapi import FastAPI

from chatbot.agent.checkpoint import create_sqlite_checkpointer
from chatbot.agent.graph import create_multi_turn_agent_graph
from chatbot.agent.model import create_tool_calling_model
from chatbot.agent.tools import create_agent_tools
from chatbot.agent.turn_analysis import create_turn_analyzer
from chatbot.embedding import load_encoder
from chatbot.graph import create_rag_graph
from chatbot.observability.langfeather import configure_langfeather, wrap_runnable
from chatbot.retriever import DEFAULT_TOP_K
from chatbot.vectorstore import open_collection

LANGFEATHER_TRACE_NAME = "korean-chatbot-rag"
LANGFEATHER_AGENT_TRACE_NAME = "korean-chatbot-agent"


def prepare_rag_resources(app: FastAPI) -> None:
    """필요 시 RAG 임베딩 모델과 벡터스토어 준비"""
    if not hasattr(app.state, "encoder"):
        app.state.encoder = load_encoder()
    if not hasattr(app.state, "collection"):
        app.state.collection = open_collection()
    if not hasattr(app.state, "rag_graph"):
        rag_graph = create_rag_graph(
            generator=app.state.generator,
            encoder=app.state.encoder,
            collection=app.state.collection,
            top_k=DEFAULT_TOP_K,
        )
        app.state.langfeather_sdk = configure_langfeather()
        app.state.rag_graph = wrap_runnable(
            rag_graph,
            sdk=app.state.langfeather_sdk,
            name=LANGFEATHER_TRACE_NAME,
        )


def prepare_agent_resources(app: FastAPI) -> None:
    """공유 자원과 SQLite Checkpointer로 멀티턴 Agent Graph 준비"""
    if hasattr(app.state, "agent_graph"):
        return

    prepare_rag_resources(app)
    agent_checkpointer = create_sqlite_checkpointer()
    agent_graph = create_multi_turn_agent_graph(
        model=create_tool_calling_model(),
        tools=create_agent_tools(
            encoder=app.state.encoder,
            collection=app.state.collection,
            top_k=DEFAULT_TOP_K,
        ),
        analyze_turn=create_turn_analyzer(generator=app.state.generator),
        checkpointer=agent_checkpointer,
    )
    app.state.agent_graph = wrap_runnable(
        agent_graph,
        sdk=app.state.langfeather_sdk,
        name=LANGFEATHER_AGENT_TRACE_NAME,
    )
    app.state.agent_checkpointer = agent_checkpointer
