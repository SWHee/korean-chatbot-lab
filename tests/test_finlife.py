"""금융상품 한눈에 정기예금 API client 계약 검증"""

import os

import pytest

import chatbot.finlife as finlife_module
from chatbot.settings import load_local_env


class FakeResponse:
    """Finlife JSON 응답의 최소 대역"""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.status_checked = False

    def raise_for_status(self) -> None:
        self.status_checked = True

    def json(self) -> dict:
        return self.payload


def _deposit_option(
    *,
    product_code: str,
    company_name: str,
    product_name: str,
    term_months: int,
    base_interest_rate: float | None,
    max_interest_rate: float | None,
) -> finlife_module.DepositProductOption:
    """상품 비교 테스트용 정규화 옵션"""
    return finlife_module.DepositProductOption(
        disclosure_month="202607",
        company_code=f"CO-{company_name}",
        product_code=product_code,
        company_name=company_name,
        product_name=product_name,
        term_months=term_months,
        base_interest_rate=base_interest_rate,
        max_interest_rate=max_interest_rate,
    )


def _saving_option(
    *,
    product_code: str,
    company_name: str,
    product_name: str,
    term_months: int,
    base_interest_rate: float | None,
    max_interest_rate: float | None,
    reserve_type: str,
    reserve_type_name: str,
):
    """적금 비교 테스트용 정규화 옵션"""
    return finlife_module.SavingProductOption(
        disclosure_month="202607",
        company_code=f"CO-{company_name}",
        product_code=product_code,
        company_name=company_name,
        product_name=product_name,
        term_months=term_months,
        base_interest_rate=base_interest_rate,
        max_interest_rate=max_interest_rate,
        reserve_type=reserve_type,
        reserve_type_name=reserve_type_name,
    )


def test_fetch_deposit_products_returns_raw_result(monkeypatch) -> None:
    """HTTP와 본문 성공 확인 후 원본 result 반환"""
    result = {
        "err_cd": "000",
        "err_msg": "정상",
        "total_count": "1",
        "max_page_no": "1",
        "now_page_no": "1",
        "baseList": [{"fin_prdt_cd": "DEPOSIT-001"}],
        "optionList": [{"fin_prdt_cd": "DEPOSIT-001", "save_trm": "12"}],
    }
    response = FakeResponse({"result": result})
    request = {}

    def fake_get(url, *, params, timeout):
        request.update(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )
        return response

    monkeypatch.setenv(finlife_module.FINLIFE_API_KEY_ENV, "test-api-key")
    monkeypatch.setattr(finlife_module.httpx, "get", fake_get)

    actual = finlife_module.fetch_deposit_products()

    assert actual == result
    assert response.status_checked is True
    assert request == {
        "url": finlife_module.FINLIFE_DEPOSIT_URL,
        "params": {
            "auth": "test-api-key",
            "topFinGrpNo": finlife_module.DEFAULT_TOP_FIN_GROUP_NO,
            "pageNo": finlife_module.DEFAULT_PAGE_NO,
        },
        "timeout": finlife_module.FINLIFE_TIMEOUT_SECONDS,
    }


def test_fetch_deposit_products_rejects_body_error(monkeypatch) -> None:
    """HTTP 200이어도 Finlife 본문 오류 거부"""
    response = FakeResponse(
        {
            "result": {
                "err_cd": "101",
                "err_msg": "topFinGrpNo의 부적절한 값",
            }
        }
    )

    monkeypatch.setenv(finlife_module.FINLIFE_API_KEY_ENV, "test-api-key")
    monkeypatch.setattr(
        finlife_module.httpx,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        RuntimeError,
        match="101.*topFinGrpNo의 부적절한 값",
    ):
        finlife_module.fetch_deposit_products(top_fin_group_no="invalid")

    assert response.status_checked is True


def test_fetch_saving_products_returns_raw_result(monkeypatch) -> None:
    """적금 endpoint의 원본 result와 적립 방식 필드 보존"""
    result = {
        "err_cd": "000",
        "err_msg": "정상",
        "baseList": [{"fin_prdt_cd": "SAVING-001"}],
        "optionList": [
            {
                "fin_prdt_cd": "SAVING-001",
                "save_trm": "12",
                "rsrv_type": "S",
                "rsrv_type_nm": "정액적립식",
            }
        ],
    }
    response = FakeResponse({"result": result})
    request = {}

    def fake_get(url, *, params, timeout):
        request.update(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )
        return response

    monkeypatch.setenv(finlife_module.FINLIFE_API_KEY_ENV, "test-api-key")
    monkeypatch.setattr(finlife_module.httpx, "get", fake_get)

    actual = finlife_module.fetch_saving_products()

    assert actual == result
    assert response.status_checked is True
    assert request["url"] == finlife_module.FINLIFE_SAVING_URL
    assert request["params"] == {
        "auth": "test-api-key",
        "topFinGrpNo": finlife_module.DEFAULT_TOP_FIN_GROUP_NO,
        "pageNo": finlife_module.DEFAULT_PAGE_NO,
    }
    assert request["timeout"] == finlife_module.FINLIFE_TIMEOUT_SECONDS


def test_fetch_saving_products_rejects_body_error(monkeypatch) -> None:
    """적금 endpoint의 HTTP 200 본문 오류 거부"""
    response = FakeResponse(
        {
            "result": {
                "err_cd": "101",
                "err_msg": "topFinGrpNo의 부적절한 값",
            }
        }
    )

    monkeypatch.setenv(finlife_module.FINLIFE_API_KEY_ENV, "test-api-key")
    monkeypatch.setattr(
        finlife_module.httpx,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        RuntimeError,
        match="101.*topFinGrpNo의 부적절한 값",
    ):
        finlife_module.fetch_saving_products(top_fin_group_no="invalid")

    assert response.status_checked is True


def test_normalize_saving_products_keeps_reserve_type() -> None:
    """적금 옵션의 적립 방식과 기간별 금리 보존"""
    result = {
        "baseList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "SAVING-001",
                "kor_co_nm": "테스트은행",
                "fin_prdt_nm": "테스트적금",
            }
        ],
        "optionList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "SAVING-001",
                "save_trm": "12",
                "intr_rate": 3.2,
                "intr_rate2": 3.8,
                "rsrv_type": "F",
                "rsrv_type_nm": "자유적립식",
            }
        ],
    }

    products = finlife_module.normalize_saving_products(result)

    assert [product.model_dump() for product in products] == [
        {
            "product_type": "saving",
            "disclosure_month": "202607",
            "company_code": "001",
            "product_code": "SAVING-001",
            "company_name": "테스트은행",
            "product_name": "테스트적금",
            "term_months": 12,
            "base_interest_rate": 3.2,
            "max_interest_rate": 3.8,
            "reserve_type": "F",
            "reserve_type_name": "자유적립식",
        }
    ]


def test_select_saving_products_filters_term_and_sorts_rate() -> None:
    """적금 기간 필터 뒤 기본금리 우선 후보 선택"""
    products = [
        _saving_option(
            product_code="HIGH",
            company_name="가은행",
            product_name="고금리적금",
            term_months=12,
            base_interest_rate=4.0,
            max_interest_rate=4.2,
            reserve_type="S",
            reserve_type_name="정액적립식",
        ),
        _saving_option(
            product_code="LOW",
            company_name="나은행",
            product_name="낮은금리적금",
            term_months=12,
            base_interest_rate=3.0,
            max_interest_rate=4.5,
            reserve_type="F",
            reserve_type_name="자유적립식",
        ),
        _saving_option(
            product_code="OTHER-TERM",
            company_name="다은행",
            product_name="6개월적금",
            term_months=6,
            base_interest_rate=9.0,
            max_interest_rate=9.0,
            reserve_type="S",
            reserve_type_name="정액적립식",
        ),
    ]

    comparison = finlife_module.select_saving_products(
        products,
        term_months=12,
        limit=1,
    )

    assert comparison.term_months == 12
    assert comparison.comparison_basis == "base_interest_rate"
    assert [product.product_code for product in comparison.products] == ["HIGH"]


def test_normalize_deposit_products_joins_product_and_rate_option() -> None:
    """세 식별 키가 같은 상품과 기간별 금리 연결"""
    result = {
        "baseList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "DEPOSIT-001",
                "kor_co_nm": "테스트은행",
                "fin_prdt_nm": "테스트예금",
            }
        ],
        "optionList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "DEPOSIT-001",
                "save_trm": "12",
                "intr_rate": 3.1,
                "intr_rate2": 3.5,
            }
        ],
    }

    products = finlife_module.normalize_deposit_products(result)

    assert [product.model_dump() for product in products] == [
        {
            "product_type": "deposit",
            "disclosure_month": "202607",
            "company_code": "001",
            "product_code": "DEPOSIT-001",
            "company_name": "테스트은행",
            "product_name": "테스트예금",
            "term_months": 12,
            "base_interest_rate": 3.1,
            "max_interest_rate": 3.5,
        }
    ]


def test_normalize_deposit_products_preserves_null_and_excludes_unknown_option(
) -> None:
    """금리 null 보존과 상품 정보가 없는 옵션 제외"""
    result = {
        "baseList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "DEPOSIT-001",
                "kor_co_nm": "테스트은행",
                "fin_prdt_nm": "테스트예금",
            }
        ],
        "optionList": [
            {
                "dcls_month": "202607",
                "fin_co_no": "001",
                "fin_prdt_cd": "DEPOSIT-001",
                "save_trm": "6",
                "intr_rate": None,
                "intr_rate2": None,
            },
            {
                "dcls_month": "202607",
                "fin_co_no": "999",
                "fin_prdt_cd": "UNKNOWN",
                "save_trm": "12",
                "intr_rate": 9.9,
                "intr_rate2": 9.9,
            },
        ],
    }

    products = finlife_module.normalize_deposit_products(result)

    assert len(products) == 1
    assert products[0].term_months == 6
    assert products[0].base_interest_rate is None
    assert products[0].max_interest_rate is None


def test_select_deposit_products_filters_sorts_ties_and_limits() -> None:
    """기간 필터와 기본금리 정렬, 동률 순서, 후보 수 제한"""
    products = [
        _deposit_option(
            product_code="HIGH",
            company_name="다은행",
            product_name="고금리예금",
            term_months=12,
            base_interest_rate=4.0,
            max_interest_rate=4.2,
        ),
        _deposit_option(
            product_code="TIE-B",
            company_name="나은행",
            product_name="동률예금",
            term_months=12,
            base_interest_rate=3.5,
            max_interest_rate=4.5,
        ),
        _deposit_option(
            product_code="TIE-A",
            company_name="가은행",
            product_name="동률예금",
            term_months=12,
            base_interest_rate=3.5,
            max_interest_rate=4.1,
        ),
        _deposit_option(
            product_code="LOW",
            company_name="라은행",
            product_name="낮은금리예금",
            term_months=12,
            base_interest_rate=2.0,
            max_interest_rate=2.5,
        ),
        _deposit_option(
            product_code="OTHER-TERM",
            company_name="마은행",
            product_name="6개월예금",
            term_months=6,
            base_interest_rate=9.0,
            max_interest_rate=9.0,
        ),
        _deposit_option(
            product_code="NO-RATE",
            company_name="바은행",
            product_name="금리미공시예금",
            term_months=12,
            base_interest_rate=None,
            max_interest_rate=9.0,
        ),
    ]

    comparison = finlife_module.select_deposit_products(
        products,
        term_months=12,
    )

    assert comparison.term_months == 12
    assert comparison.comparison_basis == "base_interest_rate"
    assert [product.product_code for product in comparison.products] == [
        "HIGH",
        "TIE-A",
        "TIE-B",
    ]


def test_select_deposit_products_uses_requested_interest_rate() -> None:
    """최고금리를 선택한 경우 해당 금리 기준 정렬"""
    products = [
        _deposit_option(
            product_code="HIGH-BASE",
            company_name="가은행",
            product_name="기본금리예금",
            term_months=12,
            base_interest_rate=4.0,
            max_interest_rate=4.1,
        ),
        _deposit_option(
            product_code="HIGH-MAX",
            company_name="나은행",
            product_name="최고금리예금",
            term_months=12,
            base_interest_rate=3.0,
            max_interest_rate=5.0,
        ),
    ]

    comparison = finlife_module.select_deposit_products(
        products,
        term_months=12,
        sort_by="max_interest_rate",
        limit=1,
    )

    assert comparison.comparison_basis == "max_interest_rate"
    assert [product.product_code for product in comparison.products] == [
        "HIGH-MAX"
    ]


def test_select_deposit_products_rejects_invalid_options() -> None:
    """지원하지 않는 정렬 기준과 후보 수 거부"""
    with pytest.raises(ValueError, match="sort_by"):
        finlife_module.select_deposit_products(
            [],
            term_months=12,
            sort_by="unknown",
        )

    with pytest.raises(ValueError, match="limit"):
        finlife_module.select_deposit_products(
            [],
            term_months=12,
            limit=0,
        )


@pytest.mark.skipif(
    os.getenv("RUN_FINLIFE_LIVE_TEST") != "1",
    reason="실제 Finlife 호출은 명시적으로 실행",
)
def test_fetch_deposit_products_live_smoke() -> None:
    """발급 키로 은행권 정기예금 호출과 정규화 확인"""
    load_local_env()

    result = finlife_module.fetch_deposit_products()
    products = finlife_module.normalize_deposit_products(result)

    assert result["err_cd"] == finlife_module.FINLIFE_SUCCESS_CODE
    assert isinstance(result["baseList"], list)
    assert isinstance(result["optionList"], list)
    assert products
    assert all(isinstance(product.term_months, int) for product in products)


@pytest.mark.skipif(
    os.getenv("RUN_FINLIFE_LIVE_TEST") != "1",
    reason="실제 Finlife 호출은 명시적으로 실행",
)
def test_fetch_saving_products_live_smoke() -> None:
    """발급 키로 은행권 적금 1페이지 응답 계약 확인"""
    load_local_env()

    result = finlife_module.fetch_saving_products()

    assert result["err_cd"] == finlife_module.FINLIFE_SUCCESS_CODE
    assert isinstance(result["baseList"], list)
    assert isinstance(result["optionList"], list)
    assert result["optionList"]
    assert {
        "rsrv_type",
        "rsrv_type_nm",
    } <= result["optionList"][0].keys()
