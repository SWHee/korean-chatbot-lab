"""법령 Retrieval과 답변 생성을 연결하는 LangGraph"""

from typing import NotRequired, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from chatbot.rag import answer_question, stream_answer_question
from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles


class RagState(TypedDict):
    """법령 RAG 그래프의 처리 상태"""

    question: str
    articles: NotRequired[list[dict]]
    answer: NotRequired[str]
    streaming: NotRequired[bool]


def create_rag_graph(
    generator,
    encoder,
    collection,
    top_k: int = DEFAULT_TOP_K,
):
    """법령 검색과 답변 생성을 순서대로 연결한 Graph"""

    def retrieve_node(state: RagState) -> dict:
        articles = retrieve_articles(
            encoder=encoder,
            collection=collection,
            question=state["question"],
            top_k=top_k,
        )
        return {"articles": articles}

    def generate_node(state: RagState) -> dict:
        if state.get("streaming", False):
            write_chunk = get_stream_writer()
            answer_chunks = []
            for chunk in stream_answer_question(
                generator=generator,
                question=state["question"],
                articles=state["articles"],
            ):
                write_chunk(chunk)
                answer_chunks.append(chunk)
            return {"answer": "".join(answer_chunks)}

        return {
            "answer": answer_question(
                generator=generator,
                question=state["question"],
                articles=state["articles"],
            )
        }

    builder = StateGraph(RagState)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    return builder.compile()
