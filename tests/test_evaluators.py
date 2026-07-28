"""검색 조문 ID 기반 평가 함수 단위 테스트"""

from types import SimpleNamespace

import pytest
from google.genai.errors import ServerError
from pydantic import ValidationError

from chatbot.evaluators import (
    JudgeResult,
    build_faithfulness_feedback,
    evaluate_faithfulness_run,
    evaluate_retrieval_run,
    score_article_retrieval_top_5,
)


def article(law_name: str, article_no: str) -> dict:
    """테스트용 법령 조문 ID"""
    return {"law_name": law_name, "article_no": article_no}


def test_judge_result_keeps_three_small_fields() -> None:
    """Judge 점수·이유·문제 목록의 최소 출력 계약"""
    result = JudgeResult(
        score=0.5,
        reason="중심 결론은 근거가 있지만 일부 주장은 확인할 수 없습니다.",
        issues=["보호 기관에 관한 설명이 검색 문맥에 없습니다."],
    )

    assert result.model_dump() == {
        "score": 0.5,
        "reason": "중심 결론은 근거가 있지만 일부 주장은 확인할 수 없습니다.",
        "issues": ["보호 기관에 관한 설명이 검색 문맥에 없습니다."],
    }


def test_judge_result_rejects_undefined_score() -> None:
    """설명하기 어려운 임의 점수 생성 방지"""
    with pytest.raises(ValidationError):
        JudgeResult(score=0.7, reason="임의 점수", issues=[])


def test_build_faithfulness_feedback_keeps_issues_in_extra() -> None:
    """Judge 문제 목록을 LangSmith Feedback 추가 정보로 보존"""
    result = JudgeResult(
        score=0.5,
        reason="일부 주장이 검색 문맥과 모순됩니다.",
        issues=["이자 제외 주장이 검색 문맥과 모순됩니다."],
    )

    feedback = build_faithfulness_feedback(result)

    assert feedback == {
        "key": "faithfulness",
        "score": 0.5,
        "comment": (
            "일부 주장이 검색 문맥과 모순됩니다.\n"
            "문제된 주장:\n"
            "- 이자 제외 주장이 검색 문맥과 모순됩니다."
        ),
        "extra": {
            "issues": ["이자 제외 주장이 검색 문맥과 모순됩니다."],
        },
    }


def test_evaluate_faithfulness_run_marks_judge_503_for_retry() -> None:
    """Judge 과부하를 점수와 구분되는 재평가 대상으로 기록"""

    class UnavailableJudge:
        def invoke(self, inputs):
            raise ServerError(
                503,
                {
                    "error": {
                        "code": 503,
                        "message": "The model is overloaded.",
                        "status": "UNAVAILABLE",
                    }
                },
            )

    run = SimpleNamespace(
        inputs={"question": "예금은 얼마까지 보호되나요?"},
        outputs={
            "retrieved_contexts": ["보험금의 한도는 1억원이다."],
            "answer": "예금은 1억원까지 보호됩니다.",
        },
    )
    example = SimpleNamespace(
        metadata={
            "rubric": {
                "metric_eligibility": {"faithfulness": True},
            }
        }
    )

    feedback = evaluate_faithfulness_run(
        run=run,
        example=example,
        judge_chain=UnavailableJudge(),
    )

    assert feedback["score"] is None
    assert "채점을 보류" in feedback["comment"]
    assert feedback["extra"] == {
        "error_type": "ServerError",
        "status_code": 503,
        "retryable": True,
    }


def test_evaluate_faithfulness_run_returns_judge_feedback() -> None:
    """정상 Judge 결과를 기존 Faithfulness feedback으로 변환"""

    class SuccessfulJudge:
        def invoke(self, inputs):
            assert inputs == {
                "question": "예금은 얼마까지 보호되나요?",
                "contexts": "보험금의 한도는 1억원이다.",
                "answer": "예금은 1억원까지 보호됩니다.",
            }
            return JudgeResult(
                score=1.0,
                reason="답변의 금액이 검색 문맥으로 뒷받침됩니다.",
                issues=[],
            )

    run = SimpleNamespace(
        inputs={"question": "예금은 얼마까지 보호되나요?"},
        outputs={
            "retrieved_contexts": ["보험금의 한도는 1억원이다."],
            "answer": "예금은 1억원까지 보호됩니다.",
        },
    )
    example = SimpleNamespace(
        metadata={
            "rubric": {
                "metric_eligibility": {"faithfulness": True},
            }
        }
    )

    feedback = evaluate_faithfulness_run(
        run=run,
        example=example,
        judge_chain=SuccessfulJudge(),
    )

    assert feedback == {
        "key": "faithfulness",
        "score": 1.0,
        "comment": "답변의 금액이 검색 문맥으로 뒷받침됩니다.",
        "extra": {"issues": []},
    }


def test_evaluate_faithfulness_run_keeps_non_503_error_visible() -> None:
    """과부하가 아닌 Judge 서버 오류를 숨기지 않음"""

    class BrokenJudge:
        def invoke(self, inputs):
            raise ServerError(
                500,
                {
                    "error": {
                        "code": 500,
                        "message": "Internal error.",
                        "status": "INTERNAL",
                    }
                },
            )

    run = SimpleNamespace(
        inputs={"question": "질문"},
        outputs={"retrieved_contexts": ["문맥"], "answer": "답변"},
    )
    example = SimpleNamespace(
        metadata={
            "rubric": {
                "metric_eligibility": {"faithfulness": True},
            }
        }
    )

    with pytest.raises(ServerError) as error:
        evaluate_faithfulness_run(
            run=run,
            example=example,
            judge_chain=BrokenJudge(),
        )

    assert error.value.code == 500


def test_score_article_retrieval_top_5_uses_required_and_supporting_articles() -> None:
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

    scores = score_article_retrieval_top_5(
        sources=sources,
        required_articles=required_articles,
        supporting_articles=supporting_articles,
    )

    assert scores == {
        "precision_top_5": 0.4,
        "recall_top_5": 0.5,
    }


def test_score_article_retrieval_top_5_returns_zero_for_empty_results() -> None:
    """검색 결과가 없으면 두 점수 모두 0"""
    scores = score_article_retrieval_top_5(
        sources=[],
        required_articles=[article("예금자보호법", "제32조")],
        supporting_articles=[],
    )

    assert scores == {
        "precision_top_5": 0.0,
        "recall_top_5": 0.0,
    }


def test_score_article_retrieval_top_5_rejects_non_retrieval_question() -> None:
    """필수 정답 조문이 없는 제외 문항의 잘못된 검색 채점 방지"""
    with pytest.raises(ValueError, match="검색 평가 대상이 아닙니다"):
        score_article_retrieval_top_5(
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
        metadata={
            "rubric": {
                "retrieval_eligible": True,
                "required_articles": [article("예금자보호법", "제32조")],
                "supporting_articles": [],
            }
        }
    )

    result = evaluate_retrieval_run(run, example)

    assert result == {
        "results": [
            {"key": "precision_top_5", "score": 0.5},
            {"key": "recall_top_5", "score": 1.0},
        ]
    }


def test_evaluate_retrieval_run_skips_non_retrieval_question() -> None:
    """검색 평가 제외 문항을 0점과 구분"""
    run = SimpleNamespace(outputs={"sources": []})
    example = SimpleNamespace(metadata={"rubric": {"retrieval_eligible": False}})

    result = evaluate_retrieval_run(run, example)

    assert [item["score"] for item in result["results"]] == [None, None]
    assert all("평가 대상이 아닌" in item["comment"] for item in result["results"])
