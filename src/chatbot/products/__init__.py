"""예·적금 조회와 비교"""

from chatbot.products.client import (
    DEFAULT_PAGE_NO,
    DEFAULT_TOP_FIN_GROUP_NO,
    FINLIFE_API_KEY_ENV,
    FINLIFE_DEPOSIT_URL,
    FINLIFE_SAVING_URL,
    FINLIFE_SUCCESS_CODE,
    FINLIFE_TIMEOUT_SECONDS,
    fetch_deposit_products,
    fetch_financial_products,
    fetch_saving_products,
)
from chatbot.products.comparison import (
    normalize_deposit_products,
    normalize_saving_products,
    select_deposit_products,
    select_saving_products,
)
from chatbot.products.models import (
    DEFAULT_PRODUCT_LIMIT,
    DEFAULT_PRODUCT_SORT_BY,
    DepositProductComparison,
    DepositProductOption,
    FinancialProductOption,
    ProductSortBy,
    ProductType,
    SavingProductComparison,
    SavingProductOption,
)


__all__ = [
    "DEFAULT_PAGE_NO",
    "DEFAULT_PRODUCT_LIMIT",
    "DEFAULT_PRODUCT_SORT_BY",
    "DEFAULT_TOP_FIN_GROUP_NO",
    "DepositProductComparison",
    "DepositProductOption",
    "FINLIFE_API_KEY_ENV",
    "FINLIFE_DEPOSIT_URL",
    "FINLIFE_SAVING_URL",
    "FINLIFE_SUCCESS_CODE",
    "FINLIFE_TIMEOUT_SECONDS",
    "FinancialProductOption",
    "ProductSortBy",
    "ProductType",
    "SavingProductComparison",
    "SavingProductOption",
    "fetch_deposit_products",
    "fetch_financial_products",
    "fetch_saving_products",
    "normalize_deposit_products",
    "normalize_saving_products",
    "select_deposit_products",
    "select_saving_products",
]
