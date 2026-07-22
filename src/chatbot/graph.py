from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from chatbot.rag import answer_question
from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles


# TypedDict: 이 딕셔너리는 이런 키/타입 구조를 갖는다"라는 타입 힌트 역할을 한다
# 법령 RAG에서 노드가 공유하는 상태 구조
class RagState(TypedDict):
    """법령 RAG 그래프의 처리 상태"""

    question: str
    articles: NotRequired[list[dict]]
    answer: NotRequired[str]


# 기존 RAG 자원을 노드에 연결한 그래프 생성
def create_rag_graph(
    generator,
    encoder,
    collection,
    top_k: int = DEFAULT_TOP_K,
):
    """기존 검색과 생성을 연결한 법령 RAG 그래프"""

    def retrieve_node(state: RagState) -> dict:
        articles = retrieve_articles(
            encoder=encoder,
            collection=collection,
            question=state["question"],
            top_k=top_k,
        )
        return {"articles": articles}

    def generate_node(state: RagState) -> dict:
        answer = answer_question(
            generator=generator,
            question=state["question"],
            articles=state["articles"],
        )
        return {"answer": answer}

    builder = StateGraph(RagState)

    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    return builder.compile()
