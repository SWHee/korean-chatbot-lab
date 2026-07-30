"""금융상품 한눈에 예·적금 API client"""

import os
from typing import Literal

import httpx
from pydantic import BaseModel


FINLIFE_DEPOSIT_URL = (
    "https://finlife.fss.or.kr/finlifeapi/depositProductsSearch.json"
)
FINLIFE_SAVING_URL = (
    "https://finlife.fss.or.kr/finlifeapi/savingProductsSearch.json"
)
FINLIFE_API_KEY_ENV = "FINLIFE_API_KEY"
FINLIFE_SUCCESS_CODE = "000"
DEFAULT_TOP_FIN_GROUP_NO = "020000"
DEFAULT_PAGE_NO = 1
FINLIFE_TIMEOUT_SECONDS = 10.0
DEFAULT_PRODUCT_LIMIT = 3  # 최종 상품 후보 수, 이후 5개와 비교할 임시 값

ProductType = Literal["deposit", "saving"]
FINLIFE_PRODUCT_URLS: dict[ProductType, str] = {
    "deposit": FINLIFE_DEPOSIT_URL,
    "saving": FINLIFE_SAVING_URL,
}
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


def _product_key(product: dict) -> tuple[str, str, str]:
    """공시월·금융회사·상품 코드를 묶은 연결 키"""
    return (
        product["dcls_month"],
        product["fin_co_no"],
        product["fin_prdt_cd"],
    )


def fetch_financial_products(
    *,
    product_type: ProductType,
    top_fin_group_no: str = DEFAULT_TOP_FIN_GROUP_NO,
    page_no: int = DEFAULT_PAGE_NO,
) -> dict:
    """은행권 예·적금 한 페이지의 Finlife 원본 result 조회"""
    api_key = os.environ[FINLIFE_API_KEY_ENV]
    params = {
        "auth": api_key,
        "topFinGrpNo": top_fin_group_no,
        "pageNo": page_no,
    }

    response = httpx.get(
        FINLIFE_PRODUCT_URLS[product_type],
        params=params,
        timeout=FINLIFE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    result = response.json()["result"]
    if result["err_cd"] != FINLIFE_SUCCESS_CODE:
        raise RuntimeError(
            f"Finlife API error {result['err_cd']}: {result['err_msg']}"
        )

    return result


def fetch_deposit_products(
    *,
    top_fin_group_no: str = DEFAULT_TOP_FIN_GROUP_NO,
    page_no: int = DEFAULT_PAGE_NO,
) -> dict:
    """은행권 정기예금 한 페이지의 Finlife 원본 result 조회"""
    return fetch_financial_products(
        product_type="deposit",
        top_fin_group_no=top_fin_group_no,
        page_no=page_no,
    )


def fetch_saving_products(
    *,
    top_fin_group_no: str = DEFAULT_TOP_FIN_GROUP_NO,
    page_no: int = DEFAULT_PAGE_NO,
) -> dict:
    """은행권 적금 한 페이지의 Finlife 원본 result 조회"""
    return fetch_financial_products(
        product_type="saving",
        top_fin_group_no=top_fin_group_no,
        page_no=page_no,
    )


def normalize_deposit_products(
    result: dict,
) -> list[DepositProductOption]:
    """상품 기본정보와 기간별 금리를 내부 비교 단위로 변환"""
    product_by_key = {
        _product_key(product_info): product_info
        for product_info in result["baseList"]
    }
    normalized_products = []  # 내부 필드명과 타입으로 변환한 상품 옵션 목록

    for rate_option in result["optionList"]:
        product_info = product_by_key.get(_product_key(rate_option))
        if product_info is None:
            continue

        normalized_products.append(
            DepositProductOption(
                disclosure_month=rate_option["dcls_month"],
                company_code=rate_option["fin_co_no"],
                product_code=rate_option["fin_prdt_cd"],
                company_name=product_info["kor_co_nm"],
                product_name=product_info["fin_prdt_nm"],
                term_months=int(rate_option["save_trm"]),
                base_interest_rate=rate_option["intr_rate"],
                max_interest_rate=rate_option["intr_rate2"],
            )
        )

    return normalized_products


def select_deposit_products(
    products: list[DepositProductOption],
    *,
    term_months: int,
    sort_by: ProductSortBy = DEFAULT_PRODUCT_SORT_BY,
    limit: int = DEFAULT_PRODUCT_LIMIT,
) -> DepositProductComparison:
    """기간과 금리 기준으로 정기예금 비교 후보 선택"""
    if sort_by not in SUPPORTED_PRODUCT_SORT_FIELDS:
        raise ValueError(
            f"sort_by must be one of {SUPPORTED_PRODUCT_SORT_FIELDS}"
        )
    if limit < 1:
        raise ValueError("limit must be at least 1")

    candidates_with_rate = []
    for product in products:
        if product.term_months != term_months:
            continue

        selected_interest_rate = (
            product.base_interest_rate
            if sort_by == "base_interest_rate"
            else product.max_interest_rate
        )
        if selected_interest_rate is None:
            continue

        candidates_with_rate.append((product, selected_interest_rate))

    def comparison_order(
        candidate: tuple[DepositProductOption, float],
    ) -> tuple[float, str, str, str]:
        """금리 내림차순과 이름 오름차순 정렬 키"""
        product, selected_interest_rate = candidate
        return (
            -selected_interest_rate,
            product.company_name,
            product.product_name,
            product.product_code,
        )

    ranked_candidates = sorted(
        candidates_with_rate,
        key=comparison_order,
    )
    selected_products = [
        product
        for product, _ in ranked_candidates[:limit]
    ]

    return DepositProductComparison(
        term_months=term_months,
        comparison_basis=sort_by,
        products=selected_products,
    )
