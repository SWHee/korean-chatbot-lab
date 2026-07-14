"""검색 조문 ID 기반 평가 함수 단위 테스트"""

from types import SimpleNamespace

import pytest

from chatbot.evaluators import evaluate_retrieval_run, score_retrieval_at_5


def article(law_name: str, article_no: str) -> dict:
    """테스트용 법령 조문 ID"""
    return {"law_name": law_name, "article_no": article_no}


def test_score_retrieval_at_5_uses_required_and_supporting_articles() -> None:
    """필수 조문 recall과 전체 관련 조문 precision 분리"""
    sources = [
        article("예금자보호법", "제32조"),
        article("예금자보호법", "제1조"),
        article("예금자보호법", "제3조"),
        article("예금자보호법", "제7조"),
        article("예금자보호법", "제9조"),
        article("예금자보호법 시행령", "제18조"),
    ]
    required_articles = [
        article("예금자보호법", "제32조"),
        article("예금자보호법 시행령", "제18조"),
    ]
    supporting_articles = [article("예금자보호법", "제3조")]

    scores = score_retrieval_at_5(
        sources=sources,
        required_articles=required_articles,
        supporting_articles=supporting_articles,
    )

    assert scores == {
        "id_context_precision_at_5": 0.4,
        "id_context_recall_at_5": 0.5,
    }


def test_score_retrieval_at_5_returns_zero_for_empty_results() -> None:
    """검색 결과가 없으면 두 점수 모두 0"""
    scores = score_retrieval_at_5(
        sources=[],
        required_articles=[article("예금자보호법", "제32조")],
        supporting_articles=[],
    )

    assert scores == {
        "id_context_precision_at_5": 0.0,
        "id_context_recall_at_5": 0.0,
    }


def test_score_retrieval_at_5_rejects_non_retrieval_question() -> None:
    """필수 정답 조문이 없는 제외 문항의 잘못된 검색 채점 방지"""
    with pytest.raises(ValueError, match="검색 평가 대상이 아닙니다"):
        score_retrieval_at_5(
            sources=[],
            required_articles=[],
            supporting_articles=[],
        )


def test_evaluate_retrieval_run_connects_langsmith_data() -> None:
    """LangSmith run·example에서 검색 결과와 정답 조문 전달"""
    run = SimpleNamespace(
        outputs={
            "sources": [
                article("예금자보호법", "제32조"),
                article("예금자보호법", "제1조"),
            ]
        }
    )
    example = SimpleNamespace(
        outputs={
            "retrieval_eligible": True,
            "required_articles": [article("예금자보호법", "제32조")],
            "supporting_articles": [],
        }
    )

    result = evaluate_retrieval_run(run, example)

    assert result == {
        "results": [
            {"key": "id_context_precision_at_5", "score": 0.5},
            {"key": "id_context_recall_at_5", "score": 1.0},
        ]
    }


def test_evaluate_retrieval_run_skips_non_retrieval_question() -> None:
    """검색 평가 제외 문항을 0점과 구분"""
    run = SimpleNamespace(outputs={"sources": []})
    example = SimpleNamespace(outputs={"retrieval_eligible": False})

    result = evaluate_retrieval_run(run, example)

    assert [item["score"] for item in result["results"]] == [None, None]
    assert all("평가 대상이 아닌" in item["comment"] for item in result["results"])
