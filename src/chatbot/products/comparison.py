"""Finlife 원본 데이터 정규화와 비교 후보 선택"""

from chatbot.products.models import (
    DEFAULT_PRODUCT_LIMIT,
    DEFAULT_PRODUCT_SORT_BY,
    SUPPORTED_PRODUCT_SORT_FIELDS,
    DepositProductComparison,
    DepositProductOption,
    ProductSortBy,
    SavingProductComparison,
    SavingProductOption,
)


def _product_key(product: dict) -> tuple[str, str, str]:
    """공시월·금융회사·상품 코드를 묶은 연결 키"""
    return (
        product["dcls_month"],
        product["fin_co_no"],
        product["fin_prdt_cd"],
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


def normalize_saving_products(
    result: dict,
) -> list[SavingProductOption]:
    """적금 기본정보와 기간·적립방식별 금리를 내부 비교 단위로 변환"""
    product_by_key = {
        _product_key(product_info): product_info
        for product_info in result["baseList"]
    }
    normalized_products = []  # 내부 필드명과 타입으로 변환한 적금 옵션 목록

    for rate_option in result["optionList"]:
        product_info = product_by_key.get(_product_key(rate_option))
        if product_info is None:
            continue

        normalized_products.append(
            SavingProductOption(
                disclosure_month=rate_option["dcls_month"],
                company_code=rate_option["fin_co_no"],
                product_code=rate_option["fin_prdt_cd"],
                company_name=product_info["kor_co_nm"],
                product_name=product_info["fin_prdt_nm"],
                term_months=int(rate_option["save_trm"]),
                base_interest_rate=rate_option["intr_rate"],
                max_interest_rate=rate_option["intr_rate2"],
                reserve_type=rate_option["rsrv_type"],
                reserve_type_name=rate_option["rsrv_type_nm"],
            )
        )

    return normalized_products


def select_saving_products(
    products: list[SavingProductOption],
    *,
    term_months: int,
    sort_by: ProductSortBy = DEFAULT_PRODUCT_SORT_BY,
    limit: int = DEFAULT_PRODUCT_LIMIT,
) -> SavingProductComparison:
    """기간과 금리 기준으로 적금 비교 후보 선택"""
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
        candidate: tuple[SavingProductOption, float],
    ) -> tuple[float, str, str, str, str]:
        """금리 내림차순과 상품·적립방식 오름차순 정렬 키"""
        product, selected_interest_rate = candidate
        return (
            -selected_interest_rate,
            product.company_name,
            product.product_name,
            product.reserve_type,
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

    return SavingProductComparison(
        term_months=term_months,
        comparison_basis=sort_by,
        products=selected_products,
    )
