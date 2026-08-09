"""금융상품 한눈에 예·적금 API client"""

import os

import httpx

from chatbot.products.models import ProductType


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
FINLIFE_PRODUCT_URLS: dict[ProductType, str] = {
    "deposit": FINLIFE_DEPOSIT_URL,
    "saving": FINLIFE_SAVING_URL,
}


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
