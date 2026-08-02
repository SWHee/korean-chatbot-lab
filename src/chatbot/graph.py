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
from chatbot.rag import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    answer_question,
    stream_answer_question,
)
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
LawRetrievalStatus = Literal["ok", "error"]
LawStatus = Literal["ok", "insufficient_evidence", "error"]
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
- 상품을 찾으려는 의도는 있지만 상품 종류 또는 기간이 부족하면 clarify로 분류하세요.
  법령 질문이 함께 있어도 필요한 상품 조건을 먼저 확인하세요.
  이때 이미 알 수 있는 상품 조건은 product_filters에 보존하고, 빠진 필드만 missing_fields에
  넣은 뒤 한 번에 답할 수 있는 짧은 clarifying_question을 작성하세요.
- 상품 조건이 모두 있고 법령 질문도 함께 있으면 mixed로 분류하세요.
- 예·적금 상품과 금융소비자보호 법령 범위 밖 질문은 out_of_scope로 분류하세요.
- 법령 검색 결과가 부족할 가능성은 clarify 사유가 아닙니다.
- sort_by는 사용자가 따로 말하지 않으면 base_interest_rate, limit은 3을 사용하세요.
- 상품 종류는 deposit 또는 saving만 사용하세요."""

OUT_OF_SCOPE_MESSAGE = (
    "현재는 예금·적금 상품 비교와 금융소비자보호 법령 안내를 도와드릴 수 있어요.\n"
    "예: ‘12개월 정기예금을 비교해 주세요’ 또는 ‘예금자보호 한도를 알려주세요’"
)
LAW_RETRIEVAL_ERROR_MESSAGE = (
    "관련 법령 정보를 불러오지 못했어요.\n잠시 후 다시 질문해 주세요."
)
PRODUCT_API_ERROR_MESSAGE = (
    "금융상품 공시 정보를 불러오지 못했어요.\n잠시 후 다시 질문해 주세요."
)
PRODUCT_SORT_LABELS: dict[ProductSortBy, str] = {
    "base_interest_rate": "기본금리",
    "max_interest_rate": "최고금리",
}


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

    @model_validator(mode="before")
    @classmethod
    def normalize_incomplete_mixed_route(cls, data):
        """상품 조건이 부족한 mixed 결과를 추가 질문으로 전환"""
        if not isinstance(data, dict) or data.get("route") != "mixed":
            return data

        product_filters = ProductFilters.model_validate(
            data.get("product_filters") or {}
        )
        missing_fields = product_filters.missing_required_fields()
        if not missing_fields:
            return data

        normalized_data = dict(data)
        normalized_data["route"] = "clarify"
        normalized_data["product_filters"] = product_filters.model_dump()
        normalized_data["missing_fields"] = missing_fields
        if not str(data.get("clarifying_question") or "").strip():
            if missing_fields == ["product_type", "term_months"]:
                clarifying_question = (
                    "예금과 적금 중 어떤 상품을 찾으시고, "
                    "몇 개월 동안 가입할 예정인가요?"
                )
            elif missing_fields == ["product_type"]:
                clarifying_question = "예금과 적금 중 어떤 상품을 찾으시나요?"
            else:
                clarifying_question = "몇 개월 동안 가입할 상품을 찾으시나요?"
            normalized_data["clarifying_question"] = clarifying_question

        return normalized_data

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


class MixedRetrievalState(TypedDict):
    """법령·상품 병렬 조회의 입력과 결과 상태"""

    law_question: str
    product_filters: dict[str, object]
    articles: NotRequired[list[dict]]
    law_status: NotRequired[LawRetrievalStatus]
    products: NotRequired[list[DepositProductOption]]
    product_status: NotRequired[ProductStatus]


class RoutedWorkflowState(TypedDict):
    """질문 분석부터 최종 답변까지 공유하는 Workflow State"""

    question: str
    route: NotRequired[QuestionRoute]
    law_question: NotRequired[str | None]
    product_filters: NotRequired[dict[str, object] | None]
    missing_fields: NotRequired[list[MissingProductField]]
    clarifying_question: NotRequired[str | None]
    articles: NotRequired[list[dict]]
    law_status: NotRequired[LawStatus]
    law_answer: NotRequired[str]
    products: NotRequired[list[DepositProductOption]]
    product_status: NotRequired[ProductStatus]
    product_answer: NotRequired[str]
    answer: NotRequired[str]


def _analyze_question(generator, question: str) -> dict:
    """자연어 질문의 구조화 route 분석"""
    analysis = generator.generate_structured(
        messages=[
            {
                "role": "system",
                "content": QUESTION_ANALYSIS_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"질문:\n{question}",
            },
        ],
        response_model=QuestionAnalysis,
    )
    return analysis.model_dump()


def _retrieve_law_articles(
    *,
    encoder,
    collection,
    question: str,
    top_k: int,
) -> dict:
    """법령 검색 결과와 예상 가능한 오류 상태 변환"""
    try:
        articles = retrieve_articles(
            encoder=encoder,
            collection=collection,
            question=question,
            top_k=top_k,
        )
    except RuntimeError:
        return {
            "articles": [],
            "law_status": "error",
        }

    return {
        "articles": articles,
        "law_status": "ok",
    }


def _search_deposit_products(
    *,
    term_months: int,
    sort_by: ProductSortBy,
    limit: int,
) -> dict:
    """정기예금 조회 오류와 비교 결과의 Graph State 변환"""
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
        term_months=term_months,
        sort_by=sort_by,
        limit=limit,
    )
    product_status: ProductStatus = "ok" if comparison.products else "no_match"
    return {
        "products": comparison.products,
        "product_status": product_status,
    }


def _require_deposit_filters(raw_filters: dict[str, object]) -> ProductFilters:
    """정기예금 조회에 필요한 구조화 조건 검증"""
    product_filters = ProductFilters.model_validate(raw_filters)
    missing_fields = product_filters.missing_required_fields()
    if missing_fields:
        raise ValueError(
            f"product retrieval requires product fields: {missing_fields}"
        )
    if product_filters.product_type != "deposit":
        raise ValueError("product retrieval currently supports deposit only")
    return product_filters


def _format_interest_rate(rate: float | None) -> str:
    """공시 금리의 화면 표시 문자열"""
    return "미공시" if rate is None else f"{rate:.2f}%"


def _format_disclosure_month(disclosure_month: str) -> str:
    """YYYYMM 공시월의 한국어 표시"""
    if len(disclosure_month) != 6 or not disclosure_month.isdigit():
        return disclosure_month
    return f"{disclosure_month[:4]}년 {disclosure_month[4:]}월"


def _render_product_answer(
    *,
    product_filters: ProductFilters,
    products: list[DepositProductOption],
    product_status: ProductStatus,
) -> str:
    """정기예금 조회 상태와 후보의 사용자용 답변 변환"""
    term_months = product_filters.term_months
    if product_status == "error":
        return PRODUCT_API_ERROR_MESSAGE
    if product_status == "no_match":
        return (
            f"{term_months}개월 정기예금 중 비교할 수 있는 상품을 찾지 못했어요.\n"
            "기간이나 비교 기준을 바꿔 다시 확인해 주세요."
        )

    comparison_basis = PRODUCT_SORT_LABELS[product_filters.sort_by]
    product_lines = []
    for index, product in enumerate(products, start=1):
        product_lines.append(
            f"{index}. {product.company_name} · {product.product_name}\n"
            f"   기본금리 {_format_interest_rate(product.base_interest_rate)} · "
            f"최고금리 {_format_interest_rate(product.max_interest_rate)} · "
            f"공시월 {_format_disclosure_month(product.disclosure_month)}"
        )

    return (
        f"{term_months}개월 정기예금을 {comparison_basis} 기준으로 비교했어요.\n\n"
        + "\n\n".join(product_lines)
        + "\n\n공시 정보는 조회 시점 기준이며, 가입 전 금융회사의 "
        "최신 상품설명서를 확인해 주세요."
    )


# Graph 확장 순서
# 법령 RAG → 상품 Node → 고정 분기 → 질문 분석 → 혼합 병렬 → 전체 Workflow
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
        return _search_deposit_products(
            term_months=state["term_months"],
            sort_by=state["sort_by"],
            limit=state["limit"],
        )

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
        return _analyze_question(generator, state["question"])

    builder = StateGraph(QuestionAnalysisState)

    builder.add_node("analyze_question", analyze_question_node)

    builder.add_edge(START, "analyze_question")
    builder.add_edge("analyze_question", END)

    return builder.compile()


def create_mixed_retrieval_graph(
    encoder,
    collection,
    top_k: int = DEFAULT_TOP_K,
):
    """법령과 정기예금 후보를 병렬로 조회하는 혼합 경로 POC"""

    def retrieve_law_node(state: MixedRetrievalState) -> dict:
        return _retrieve_law_articles(
            encoder=encoder,
            collection=collection,
            question=state["law_question"],
            top_k=top_k,
        )

    def search_products_node(state: MixedRetrievalState) -> dict:
        product_filters = _require_deposit_filters(state["product_filters"])

        return _search_deposit_products(
            term_months=product_filters.term_months,
            sort_by=product_filters.sort_by,
            limit=product_filters.limit,
        )

    def join_results_node(state: MixedRetrievalState) -> dict:
        # 두 Branch 결과는 이미 State에 병합된 상태
        return {}

    builder = StateGraph(MixedRetrievalState)

    builder.add_node("retrieve_law", retrieve_law_node)
    builder.add_node("search_products", search_products_node)
    builder.add_node("join_results", join_results_node)

    # START에서 나뉜 두 Edge는 같은 Graph step에서 병렬 실행
    builder.add_edge(START, "retrieve_law")
    builder.add_edge(START, "search_products")
    # 서로 다른 State 키를 쓰므로 별도 Reducer 없이 두 결과 병합
    builder.add_edge(["retrieve_law", "search_products"], "join_results")
    builder.add_edge("join_results", END)

    return builder.compile()


def create_routed_workflow_graph(
    generator,
    encoder,
    collection,
    top_k: int = DEFAULT_TOP_K,
):
    """질문 분석 결과를 route별 최종 답변으로 연결하는 Workflow v1"""

    def analyze_question_node(state: RoutedWorkflowState) -> dict:
        return _analyze_question(generator, state["question"])

    def select_route(state: RoutedWorkflowState) -> QuestionRoute:
        return state["route"]

    def retrieve_law_node(state: RoutedWorkflowState) -> dict:
        return _retrieve_law_articles(
            encoder=encoder,
            collection=collection,
            question=state["law_question"],
            top_k=top_k,
        )

    def generate_law_node(state: RoutedWorkflowState) -> dict:
        if state["law_status"] == "error":
            return {"law_answer": LAW_RETRIEVAL_ERROR_MESSAGE}

        law_answer = answer_question(
            generator=generator,
            question=state["law_question"],
            articles=state["articles"],
        )
        law_status: LawStatus = (
            "insufficient_evidence"
            if law_answer == INSUFFICIENT_EVIDENCE_MESSAGE
            else "ok"
        )
        return {
            "law_answer": law_answer,
            "law_status": law_status,
        }

    def search_products_node(state: RoutedWorkflowState) -> dict:
        product_filters = _require_deposit_filters(state["product_filters"])
        return _search_deposit_products(
            term_months=product_filters.term_months,
            sort_by=product_filters.sort_by,
            limit=product_filters.limit,
        )

    def render_products_node(state: RoutedWorkflowState) -> dict:
        product_filters = _require_deposit_filters(state["product_filters"])
        return {
            "product_answer": _render_product_answer(
                product_filters=product_filters,
                products=state["products"],
                product_status=state["product_status"],
            )
        }

    def finish_single_route_node(state: RoutedWorkflowState) -> dict:
        if state["route"] == "law":
            return {"answer": state["law_answer"]}
        return {"answer": state["product_answer"]}

    def begin_mixed_node(state: RoutedWorkflowState) -> dict:
        # 분석 결과를 유지한 채 두 조회 Branch의 시작점 역할
        return {}

    def compose_mixed_node(state: RoutedWorkflowState) -> dict:
        return {
            "answer": (
                f"법령 안내\n{state['law_answer']}\n\n"
                f"상품 비교\n{state['product_answer']}"
            )
        }

    def ask_clarifying_question_node(state: RoutedWorkflowState) -> dict:
        return {"answer": state["clarifying_question"]}

    def explain_scope_node(state: RoutedWorkflowState) -> dict:
        return {"answer": OUT_OF_SCOPE_MESSAGE}

    builder = StateGraph(RoutedWorkflowState)

    builder.add_node("analyze_question", analyze_question_node)
    builder.add_node("retrieve_law", retrieve_law_node)
    builder.add_node("generate_law", generate_law_node)
    builder.add_node("search_products", search_products_node)
    builder.add_node("render_products", render_products_node)
    builder.add_node("finish_single_route", finish_single_route_node)
    builder.add_node("begin_mixed", begin_mixed_node)
    # 동일한 함수를 다른 Node 이름으로 등록해 mixed 경로를 그래프에 그대로 노출
    builder.add_node("mixed_retrieve_law", retrieve_law_node)
    builder.add_node("mixed_generate_law", generate_law_node)
    builder.add_node("mixed_search_products", search_products_node)
    builder.add_node("mixed_render_products", render_products_node)
    builder.add_node("compose_mixed", compose_mixed_node)
    builder.add_node("ask_clarifying_question", ask_clarifying_question_node)
    builder.add_node("explain_scope", explain_scope_node)

    builder.add_edge(START, "analyze_question")
    builder.add_conditional_edges(
        "analyze_question",
        select_route,
        {
            "law": "retrieve_law",
            "product": "search_products",
            "mixed": "begin_mixed",
            "clarify": "ask_clarifying_question",
            "out_of_scope": "explain_scope",
        },
    )

    builder.add_edge("retrieve_law", "generate_law")
    builder.add_edge("generate_law", "finish_single_route")
    builder.add_edge("search_products", "render_products")
    builder.add_edge("render_products", "finish_single_route")
    builder.add_edge("finish_single_route", END)

    # mixed는 조회와 렌더링까지 병렬 처리한 뒤 두 답변이 준비되면 합류
    builder.add_edge("begin_mixed", "mixed_retrieve_law")
    builder.add_edge("begin_mixed", "mixed_search_products")
    builder.add_edge("mixed_retrieve_law", "mixed_generate_law")
    builder.add_edge("mixed_search_products", "mixed_render_products")
    builder.add_edge(
        ["mixed_generate_law", "mixed_render_products"],
        "compose_mixed",
    )
    builder.add_edge("compose_mixed", END)

    builder.add_edge("ask_clarifying_question", END)
    builder.add_edge("explain_scope", END)

    return builder.compile()
