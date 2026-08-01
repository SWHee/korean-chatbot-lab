from typing import Literal, NotRequired, TypedDict

import httpx
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from chatbot.finlife import (
    DepositProductOption,  # 정규화한 기간별 정기예금 금리 정보
    ProductSortBy,  # 기본금리 / 최고금리 중 비교 기준
    fetch_deposit_products,  # Finlife 정기예금 원본 응답 조회
    normalize_deposit_products,  # 원본 상품·옵션을 내부 모델로 변환
    select_deposit_products,  # 기간·금리 기준 상위 후보 선택
)
from chatbot.rag import answer_question, stream_answer_question
from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles


# TypedDict: 이 딕셔너리는 이런 키/타입 구조를 갖는다"라는 타입 힌트 역할을 한다
# 법령 RAG에서 노드가 공유하는 상태 구조
class RagState(TypedDict):
    """법령 RAG 그래프의 처리 상태"""

    question: str
    articles: NotRequired[list[dict]]
    answer: NotRequired[str]
    streaming: NotRequired[bool]


ProductStatus = Literal["ok", "no_match", "error"]


class ProductState(TypedDict):
    """정기예금 상품 조회 그래프의 처리 상태"""

    term_months: int
    sort_by: ProductSortBy
    limit: int
    products: NotRequired[list[DepositProductOption]]
    product_status: NotRequired[ProductStatus]


def create_rag_graph(
    generator,
    encoder,
    collection,
    top_k: int = DEFAULT_TOP_K,
):
    # 기존 검색과 생성을 연결한 법령 RAG 그래프
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

        answer = answer_question(
            generator=generator,
            question=state["question"],
            articles=state["articles"],
        )
        return {"answer": answer}


    # def search_law_articles(question: str) -> RagState:
    #     # 법령 RAG 그래프를 실행하는 함수
    #     initial_state: RagState = {"question": question}
    #     final_state = builder.run(initial_state)
    #     return final_state


    # def search_financial_products(question: str) -> RagState:
    #     # 금융상품 RAG 그래프를 실행하는 함수
    #     initial_state: RagState = {"question": question}
    #     final_state = builder.run(initial_state)
    #     return final_state

    builder = StateGraph(RagState)

    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    # [Graph Visualization] 그래프를 시각화하고 싶다면 아래 주석을 해제하세요.
    # mermaid_text = builder.get_graph().draw_mermaid()
    # print(mermaid_text)

    return builder.compile()


def create_product_graph():
    """구조화 조건으로 정기예금 후보를 조회하는 단일 Node 그래프"""

    def search_products_node(state: ProductState) -> dict:
        try:
            result = fetch_deposit_products()
        except (httpx.HTTPError, RuntimeError):
            return {
                "products": [],
                "product_status": "error",
            }

        normalized_products = normalize_deposit_products(result)
        comparison = select_deposit_products(
            normalized_products,
            term_months=state["term_months"],
            sort_by=state["sort_by"],
            limit=state["limit"],
        )
        product_status: ProductStatus = (
            "ok" if comparison.products else "no_match"
        )
        return {
            "products": comparison.products,
            "product_status": product_status,
        }

    builder = StateGraph(ProductState)

    builder.add_node("search_products", search_products_node)

    builder.add_edge(START, "search_products")
    builder.add_edge("search_products", END)

    return builder.compile()
