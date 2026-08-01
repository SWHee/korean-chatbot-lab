from typing import Literal, NotRequired, TypedDict

import httpx
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, model_validator

from chatbot.finlife import (
    DEFAULT_PRODUCT_LIMIT,
    DEFAULT_PRODUCT_SORT_BY,
    DepositProductOption,  # 정규화한 기간별 정기예금 금리 정보
    ProductSortBy,  # 기본금리 / 최고금리 중 비교 기준
    ProductType,  # 정기예금·적금 상품 종류
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
FixedRoute = Literal["law", "product"]
QuestionRoute = Literal[
    "law",
    "product",
    "mixed",
    "clarify",
    "out_of_scope",
]
MissingProductField = Literal["product_type", "term_months"]

QUESTION_ANALYSIS_SYSTEM_PROMPT = """당신은 예·적금 금융 상담 챗봇의 질문 분류기입니다.
사용자에게 답변하지 말고 전달된 JSON schema에 맞는 분석 결과만 반환하세요.

- 법령·금융소비자보호 기준 질문은 law로 분류하고 law_question에 검색할 질문을 넣으세요.
- 예금 또는 적금의 비교·추천 질문에서 상품 종류와 기간이 있으면 product로 분류하세요.
- 상품 비교와 법령 질문이 함께 있으면 mixed로 분류하세요.
- 상품을 찾으려는 의도는 있지만 상품 종류 또는 기간이 부족하면 clarify로 분류하세요.
  이때 이미 알 수 있는 상품 조건은 product_filters에 보존하고, 빠진 필드만 missing_fields에
  넣은 뒤 한 번에 답할 수 있는 짧은 clarifying_question을 작성하세요.
- 예·적금 상품과 금융소비자보호 법령 범위 밖 질문은 out_of_scope로 분류하세요.
- 법령 검색 결과가 부족할 가능성은 clarify 사유가 아닙니다.
- sort_by는 사용자가 따로 말하지 않으면 base_interest_rate, limit은 3을 사용하세요.
- 상품 종류는 deposit 또는 saving만 사용하세요."""


class ProductState(TypedDict):
    """정기예금 상품 조회 그래프의 처리 상태"""

    term_months: int
    sort_by: ProductSortBy
    limit: int
    products: NotRequired[list[DepositProductOption]]
    product_status: NotRequired[ProductStatus]


class FixedRouteState(TypedDict):
    """고정 route 조건부 Edge 확인용 상태"""

    route: FixedRoute
    executed_node: NotRequired[str]


class ProductFilters(BaseModel):
    """질문에서 추출한 예·적금 비교 조건"""

    model_config = ConfigDict(extra="forbid")

    product_type: ProductType | None = None
    term_months: int | None = Field(default=None, ge=1)
    sort_by: ProductSortBy = DEFAULT_PRODUCT_SORT_BY
    limit: int = Field(default=DEFAULT_PRODUCT_LIMIT, ge=1)

    def missing_required_fields(self) -> list[MissingProductField]:
        """상품 조회 전 추가로 필요한 필드 목록"""
        missing_fields = []
        if self.product_type is None:
            missing_fields.append("product_type")
        if self.term_months is None:
            missing_fields.append("term_months")
        return missing_fields


class QuestionAnalysis(BaseModel):
    """자연어 질문을 route와 구조화 조회 조건으로 변환한 결과"""

    model_config = ConfigDict(extra="forbid")

    route: QuestionRoute
    law_question: str | None = None
    product_filters: ProductFilters | None = None
    missing_fields: list[MissingProductField] = Field(default_factory=list)
    clarifying_question: str | None = None

    @model_validator(mode="after")
    def validate_route_contract(self):
        """route별 필수·제외 필드 조합 검증"""
        has_law_question = bool(self.law_question and self.law_question.strip())
        product_ready = (
            self.product_filters is not None
            and not self.product_filters.missing_required_fields()
        )

        if self.route == "law":
            if not has_law_question:
                raise ValueError("law route requires law_question")
            if self.product_filters or self.missing_fields or self.clarifying_question:
                raise ValueError("law route must not contain product fields")
        elif self.route == "product":
            if not product_ready:
                raise ValueError("product route requires complete product_filters")
            if self.missing_fields or self.clarifying_question or self.law_question:
                raise ValueError("product route must contain only product filters")
        elif self.route == "mixed":
            if not has_law_question or not product_ready:
                raise ValueError(
                    "mixed route requires law_question and complete product_filters"
                )
            if self.missing_fields or self.clarifying_question:
                raise ValueError("mixed route must not contain clarification fields")
        elif self.route == "clarify":
            if not self.clarifying_question or not self.clarifying_question.strip():
                raise ValueError("clarify route requires clarifying_question")
            expected_fields = (
                self.product_filters.missing_required_fields()
                if self.product_filters is not None
                else ["product_type", "term_months"]
            )
            if self.missing_fields != expected_fields:
                raise ValueError("clarify route missing_fields must match product_filters")
        elif (
            has_law_question
            or self.product_filters
            or self.missing_fields
            or self.clarifying_question
        ):
            raise ValueError("out_of_scope route must not contain analysis details")

        return self


class QuestionAnalysisState(TypedDict):
    """질문 분석 Node의 입력과 출력 상태"""

    question: str
    route: NotRequired[QuestionRoute]
    law_question: NotRequired[str | None]
    product_filters: NotRequired[dict[str, object] | None]
    missing_fields: NotRequired[list[MissingProductField]]
    clarifying_question: NotRequired[str | None]


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


def create_fixed_route_graph():
    """State route에 따라 한 개 Node를 선택하는 조건부 Edge 그래프"""

    def select_route(state: FixedRouteState) -> FixedRoute:
        return state["route"]

    def law_node(state: FixedRouteState) -> dict:
        return {"executed_node": "law_node"}

    def product_node(state: FixedRouteState) -> dict:
        return {"executed_node": "product_node"}

    builder = StateGraph(FixedRouteState)

    builder.add_node("law_node", law_node)
    builder.add_node("product_node", product_node)
    builder.add_conditional_edges(
        START,
        select_route,
        {
            "law": "law_node",
            "product": "product_node",
        },
    )
    builder.add_edge("law_node", END)
    builder.add_edge("product_node", END)

    return builder.compile()


def create_question_analysis_graph(generator):
    """자연어 질문을 구조화 route State로 변환하는 단일 Node 그래프"""

    def analyze_question_node(state: QuestionAnalysisState) -> dict:
        analysis = generator.generate_structured(
            messages=[
                {
                    "role": "system",
                    "content": QUESTION_ANALYSIS_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"질문:\n{state['question']}",
                },
            ],
            response_model=QuestionAnalysis,
        )
        return analysis.model_dump()

    builder = StateGraph(QuestionAnalysisState)

    builder.add_node("analyze_question", analyze_question_node)

    builder.add_edge(START, "analyze_question")
    builder.add_edge("analyze_question", END)

    return builder.compile()
