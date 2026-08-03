"""법령·금융상품 Tool 입력 계약"""

import httpx
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, ConfigDict, Field, model_validator

from chatbot.finlife import (
    DEFAULT_PRODUCT_LIMIT,
    DEFAULT_PRODUCT_SORT_BY,
    ProductSortBy,
    ProductType,
    fetch_deposit_products,
    normalize_deposit_products,
    select_deposit_products,
)
from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles


class SearchLawArticlesInput(BaseModel):
    """금융소비자보호 법령 검색에 필요한 질문"""

    model_config = ConfigDict(
        extra="forbid",
        title="search_law_articles",
    )

    question: str = Field(
        min_length=1,
        description="법령 벡터 검색에 사용할 구체적인 한국어 질문",
    )


class SearchFinancialProductsInput(BaseModel):
    """Finlife 예·적금 비교에 필요한 조건"""

    model_config = ConfigDict(
        extra="forbid",
        title="search_financial_products",
    )

    product_type: ProductType = Field(description="상품 종류: deposit 또는 saving")
    term_months: int = Field(description="가입 기간(개월, 1 이상)")
    sort_by: ProductSortBy = Field(
        default=DEFAULT_PRODUCT_SORT_BY,
        description="비교 기준: 기본금리 또는 최고금리",
    )
    limit: int = Field(
        default=DEFAULT_PRODUCT_LIMIT,
        description="반환할 상품 후보 수(1 이상)",
    )

    @model_validator(mode="after")
    def validate_positive_numbers(self):
        """Anthropic strict schema 밖의 양수 범위 검증"""
        if self.term_months < 1 or self.limit < 1:
            raise ValueError("term_months and limit must be greater than or equal to 1")
        return self


AGENT_TOOL_SCHEMAS: tuple[type[BaseModel], ...] = (
    SearchLawArticlesInput,
    SearchFinancialProductsInput,
)


def create_agent_tools(
    *,
    encoder,
    collection,
    top_k: int = DEFAULT_TOP_K,
) -> list[BaseTool]:
    """공유 검색 자원에 연결한 Agent 실행 Tool 생성"""

    @tool("search_law_articles", args_schema=SearchLawArticlesInput)
    def search_law_articles(question: str) -> dict:
        """법령 검색 결과"""
        try:
            articles = retrieve_articles(
                encoder=encoder,
                collection=collection,
                question=question,
                top_k=top_k,
            )
        except RuntimeError:
            return {
                "status": "error",
                "message": "법령 정보를 불러오지 못했습니다.",
            }

        if not articles:
            return {"status": "no_match", "articles": []}

        return {
            "status": "ok",
            "articles": [
                {
                    "source_id": f"S{index}",
                    "law_name": article["law_name"],
                    "article_no": article["article_no"],
                    "effective_date": article["effective_date"],
                    "text": article["text"],
                }
                for index, article in enumerate(articles, start=1)
            ],
        }

    @tool("search_financial_products", args_schema=SearchFinancialProductsInput)
    def search_financial_products(
        product_type: ProductType,
        term_months: int,
        sort_by: ProductSortBy = DEFAULT_PRODUCT_SORT_BY,
        limit: int = DEFAULT_PRODUCT_LIMIT,
    ) -> dict:
        """정기예금 비교 후보"""
        if product_type != "deposit":
            return {
                "status": "unsupported",
                "message": "현재는 정기예금 비교만 지원합니다.",
            }

        try:
            result = fetch_deposit_products()
        except (httpx.HTTPError, RuntimeError):
            return {
                "status": "error",
                "message": "Finlife 공시 정보를 불러오지 못했습니다.",
            }

        comparison = select_deposit_products(
            normalize_deposit_products(result),
            term_months=term_months,
            sort_by=sort_by,
            limit=limit,
        )
        if not comparison.products:
            return {
                "status": "no_match",
                "comparison_basis": comparison.comparison_basis,
                "products": [],
            }

        return {
            "status": "ok",
            "comparison_basis": comparison.comparison_basis,
            "products": [
                product.model_dump()
                for product in comparison.products
            ],
        }

    return [search_law_articles, search_financial_products]
