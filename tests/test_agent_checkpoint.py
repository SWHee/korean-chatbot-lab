"""SQLite Checkpointer 기반 Agent 상태 복원 검증"""

from langchain_core.messages import AIMessage, HumanMessage

from chatbot.agent.checkpoint import create_sqlite_checkpointer
from chatbot.agent.graph import create_agent_loop_graph


class ScriptedModel:
    """정해진 응답을 반환하는 Tool 호출 모델 대역"""

    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = iter(responses)

    def bind_tools(self, tools, *, strict):
        return self

    def invoke(self, messages) -> AIMessage:
        return next(self.responses)


def _thread_config(thread_id: str) -> dict:
    """LangGraph thread 식별 runtime 설정"""
    return {"configurable": {"thread_id": thread_id}}


def test_sqlite_checkpointer_restores_same_thread_after_reconnection(tmp_path) -> None:
    """DB 연결을 다시 만들고도 같은 thread 메시지 복원"""
    database_path = tmp_path / "langgraph.sqlite3"
    first_saver = create_sqlite_checkpointer(database_path=database_path)
    first_graph = create_agent_loop_graph(
        model=ScriptedModel([AIMessage(content="첫 번째 답변")]),
        tools=[],
        checkpointer=first_saver,
    )
    thread_config = _thread_config("conversation-1")

    first_graph.invoke(
        {"messages": [HumanMessage(content="첫 번째 질문")]},
        config=thread_config,
    )
    first_saver.conn.close()

    second_saver = create_sqlite_checkpointer(database_path=database_path)
    second_graph = create_agent_loop_graph(
        model=ScriptedModel([AIMessage(content="두 번째 답변")]),
        tools=[],
        checkpointer=second_saver,
    )
    result = second_graph.invoke(
        {"messages": [HumanMessage(content="두 번째 질문")]},
        config=thread_config,
    )
    second_saver.conn.close()

    assert [message.content for message in result["messages"]] == [
        "첫 번째 질문",
        "첫 번째 답변",
        "두 번째 질문",
        "두 번째 답변",
    ]


def test_sqlite_checkpointer_keeps_threads_separate(tmp_path) -> None:
    """다른 thread에는 이전 대화 메시지가 섞이지 않음"""
    saver = create_sqlite_checkpointer(database_path=tmp_path / "langgraph.sqlite3")
    graph = create_agent_loop_graph(
        model=ScriptedModel(
            [
                AIMessage(content="첫 thread 답변"),
                AIMessage(content="새 thread 답변"),
            ]
        ),
        tools=[],
        checkpointer=saver,
    )

    graph.invoke(
        {"messages": [HumanMessage(content="첫 thread 질문")]},
        config=_thread_config("conversation-1"),
    )
    result = graph.invoke(
        {"messages": [HumanMessage(content="새 thread 질문")]},
        config=_thread_config("conversation-2"),
    )
    saver.conn.close()

    assert [message.content for message in result["messages"]] == [
        "새 thread 질문",
        "새 thread 답변",
    ]
