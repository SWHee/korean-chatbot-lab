"""검색 조문 ID와 정답 조문을 비교하는 평가 함수"""

from langsmith.evaluation import run_evaluator
from langsmith.schemas import Example, Run


EVALUATION_TOP_K = 5


def _article_id(article: dict) -> tuple[str, str]:
    """법령명과 조문번호로 비교 가능한 ID 생성"""
    return article["law_name"], article["article_no"]


def score_retrieval_at_5(
    sources: list[dict],
    required_articles: list[dict],
    supporting_articles: list[dict],
) -> dict[str, float]:
    """top-5 조문의 ID 기반 Context Precision·Recall 계산"""
    if not required_articles:
        raise ValueError("필수 정답 조문이 없는 문항은 검색 평가 대상이 아닙니다.")

    retrieved_ids = [_article_id(source) for source in sources[:EVALUATION_TOP_K]]
    required_ids = {_article_id(article) for article in required_articles}
    supporting_ids = {_article_id(article) for article in supporting_articles}
    relevant_ids = required_ids | supporting_ids

    found_required_count = len(set(retrieved_ids) & required_ids)
    relevant_retrieved_count = sum(
        article_id in relevant_ids for article_id in retrieved_ids
    )

    recall = found_required_count / len(required_ids)
    precision = (
        relevant_retrieved_count / len(retrieved_ids) if retrieved_ids else 0.0
    )

    return {
        "id_context_precision_at_5": precision,
        "id_context_recall_at_5": recall,
    }


def evaluate_retrieval_run(run: Run, example: Example | None) -> dict:
    """LangSmith 실행 결과와 Dataset 정답 조문을 검색 점수로 연결"""
    if example is None:
        raise ValueError("검색 평가에는 Dataset example이 필요합니다.")

    reference = example.outputs or {}
    if not reference.get("retrieval_eligible", False):
        comment = "현재 법령 corpus의 검색 평가 대상이 아닌 문항"
        return {
            "results": [
                {
                    "key": "id_context_precision_at_5",
                    "score": None,
                    "comment": comment,
                },
                {
                    "key": "id_context_recall_at_5",
                    "score": None,
                    "comment": comment,
                },
            ]
        }

    outputs = run.outputs or {}
    scores = score_retrieval_at_5(
        sources=outputs["sources"],
        required_articles=reference["required_articles"],
        supporting_articles=reference["supporting_articles"],
    )

    return {
        "results": [
            {"key": key, "score": score} for key, score in scores.items()
        ]
    }


langsmith_retrieval_evaluator = run_evaluator(evaluate_retrieval_run)
