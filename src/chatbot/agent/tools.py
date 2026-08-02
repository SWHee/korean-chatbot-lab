"""법령·금융상품 Tool 입력 계약"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from chatbot.finlife import (
    DEFAULT_PRODUCT_LIMIT,
    DEFAULT_PRODUCT_SORT_BY,
    ProductSortBy,
    ProductType,
)


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
