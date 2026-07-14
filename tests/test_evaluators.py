"""검색 조문 ID 기반 평가 함수 단위 테스트"""

import pytest

from chatbot.evaluators import score_retrieval_at_5


def article(law_name: str, article_no: str) -> dict:
    """테스트용 법령 조문 ID"""
    return {"law_name": law_name, "article_no": article_no}


def test_score_retrieval_at_5_uses_primary_and_supporting_gold() -> None:
    """필수 조문 recall과 전체 관련 조문 precision 분리"""
    sources = [
        article("예금자보호법", "제32조"),
        article("예금자보호법", "제1조"),
        article("예금자보호법", "제3조"),
        article("예금자보호법", "제7조"),
        article("예금자보호법", "제9조"),
        article("예금자보호법 시행령", "제18조"),
    ]
    primary_gold = [
        article("예금자보호법", "제32조"),
        article("예금자보호법 시행령", "제18조"),
    ]
    supporting_gold = [article("예금자보호법", "제3조")]

    scores = score_retrieval_at_5(
        sources=sources,
        primary_gold_articles=primary_gold,
        supporting_gold_articles=supporting_gold,
    )

    assert scores == {
        "id_context_precision_at_5": 0.4,
        "id_context_recall_at_5": 0.5,
    }


def test_score_retrieval_at_5_returns_zero_for_empty_results() -> None:
    """검색 결과가 없으면 두 점수 모두 0"""
    scores = score_retrieval_at_5(
        sources=[],
        primary_gold_articles=[article("예금자보호법", "제32조")],
        supporting_gold_articles=[],
    )

    assert scores == {
        "id_context_precision_at_5": 0.0,
        "id_context_recall_at_5": 0.0,
    }


def test_score_retrieval_at_5_rejects_non_retrieval_question() -> None:
    """primary gold가 없는 제외 문항의 잘못된 검색 채점 방지"""
    with pytest.raises(ValueError, match="검색 평가 대상이 아닙니다"):
        score_retrieval_at_5(
            sources=[],
            primary_gold_articles=[],
            supporting_gold_articles=[],
        )
