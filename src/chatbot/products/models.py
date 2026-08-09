"""예·적금 비교 데이터 계약"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


DEFAULT_PRODUCT_LIMIT = 3  # 최종 상품 후보 수, 이후 5개와 비교할 임시 값
ProductType = Literal["deposit", "saving"]
ProductSortBy = Literal[
    "base_interest_rate",
    "max_interest_rate",
]
DEFAULT_PRODUCT_SORT_BY: ProductSortBy = "base_interest_rate"
SUPPORTED_PRODUCT_SORT_FIELDS = (
    "base_interest_rate",
    "max_interest_rate",
)


class DepositProductOption(BaseModel):
    """정기예금 상품의 기간별 금리 비교 단위"""

    product_type: Literal["deposit"] = "deposit"  # 정기예금 상품 구분값
    disclosure_month: str  # 상품 정보가 공시된 기준 연월
    company_code: str  # 금융회사를 구분하는 Finlife 코드
    product_code: str  # 금융회사 안에서 상품을 구분하는 코드
    company_name: str  # 상품을 제공하는 금융회사 이름
    product_name: str  # 정기예금 상품 이름
    term_months: int  # 예치 기간의 개월 수
    base_interest_rate: float | None  # 우대조건 적용 전 기본금리
    max_interest_rate: float | None  # 우대조건 적용 시 최고금리


class DepositProductComparison(BaseModel):
    """정해진 조건으로 고른 정기예금 비교 결과"""

    term_months: int  # 비교에 사용한 예치 기간
    comparison_basis: ProductSortBy  # 후보 순위를 정한 금리 기준
    products: list[DepositProductOption]  # 정렬과 개수 제한을 적용한 후보


class SavingProductOption(BaseModel):
    """적금 상품의 기간·적립방식별 금리 비교 단위"""

    product_type: Literal["saving"] = "saving"  # 적금 상품 구분값
    disclosure_month: str  # 상품 정보가 공시된 기준 연월
    company_code: str  # 금융회사를 구분하는 Finlife 코드
    product_code: str  # 금융회사 안에서 상품을 구분하는 코드
    company_name: str  # 상품을 제공하는 금융회사 이름
    product_name: str  # 적금 상품 이름
    term_months: int  # 가입 기간의 개월 수
    base_interest_rate: float | None  # 우대조건 적용 전 기본금리
    max_interest_rate: float | None  # 우대조건 적용 시 최고금리
    reserve_type: str  # Finlife 적립 방식 코드
    reserve_type_name: str  # 정액·자유적립식 등의 적립 방식 이름


class SavingProductComparison(BaseModel):
    """정해진 조건으로 고른 적금 비교 결과"""

    term_months: int  # 비교에 사용한 가입 기간
    comparison_basis: ProductSortBy  # 후보 순위를 정한 금리 기준
    products: list[SavingProductOption]  # 정렬과 개수 제한을 적용한 후보


FinancialProductOption = Annotated[
    DepositProductOption | SavingProductOption,
    Field(discriminator="product_type"),
]
