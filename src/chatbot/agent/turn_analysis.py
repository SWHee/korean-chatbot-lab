"""멀티턴 상품 조건 분석 계약"""

import json
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from chatbot.finlife import ProductSortBy, ProductType


TurnIntentType = Literal["law", "product", "mixed", "out_of_scope"]

TURN_ANALYSIS_SYSTEM_PROMPT = """당신은 예·적금 금융 상담 Agent의 대화 조건 분석기입니다.
사용자에게 답변하지 말고 전달된 JSON schema에 맞는 결과만 반환하세요.

- 현재 메시지와 이미 확인된 상품 조건을 함께 읽으세요.
- 예금·적금 비교·추천 의도면 product, 법령 질문이면 law, 둘 다 있으면 mixed를 선택하세요.
- 현재 지원 범위 밖이면 out_of_scope를 선택하세요.
- 사용자가 말한 상품 유형, 가입 기간, 정렬 기준, 후보 수만 채우세요.
- 이전 조건과 모순되는 새 조건이 있으면 새 조건을 반환하세요.
- 상품 유형은 deposit 또는 saving만 사용하세요."""


class TurnIntent(BaseModel):
    """현재 메시지에서 새로 확인한 대화 의도와 상품 조건"""

    model_config = ConfigDict(extra="forbid")

    intent: TurnIntentType
    product_type: ProductType | None = None
    term_months: int | None = Field(default=None, ge=1)
    sort_by: ProductSortBy | None = None
    limit: int | None = Field(default=None, ge=1)


def create_turn_analyzer(*, generator) -> Callable[..., TurnIntent]:
    """현재 메시지와 저장 조건을 함께 읽는 구조화 분석기 생성"""

    def analyze_turn(
        *,
        message: str,
        previous_preferences: dict | None,
    ) -> TurnIntent:
        known_preferences = json.dumps(
            previous_preferences or {},
            ensure_ascii=False,
        )
        return generator.generate_structured(
            messages=[
                {"role": "system", "content": TURN_ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"이미 확인된 상품 조건:\n{known_preferences}\n\n"
                        f"현재 사용자 메시지:\n{message}"
                    ),
                },
            ],
            response_model=TurnIntent,
        )

    return analyze_turn
