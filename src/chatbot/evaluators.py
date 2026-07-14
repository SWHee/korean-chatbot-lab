"""검색 조문 ID와 gold 조문을 비교하는 평가 함수"""

EVALUATION_TOP_K = 5


def _article_id(article: dict) -> tuple[str, str]:
    """법령명과 조문번호로 비교 가능한 ID 생성"""
    return article["law_name"], article["article_no"]


def score_retrieval_at_5(
    sources: list[dict],
    primary_gold_articles: list[dict],
    supporting_gold_articles: list[dict],
) -> dict[str, float]:
    """top-5 조문의 ID 기반 Context Precision·Recall 계산"""
    if not primary_gold_articles:
        raise ValueError("primary gold가 없는 문항은 검색 평가 대상이 아닙니다.")

    retrieved_ids = [_article_id(source) for source in sources[:EVALUATION_TOP_K]]
    primary_ids = {_article_id(article) for article in primary_gold_articles}
    supporting_ids = {_article_id(article) for article in supporting_gold_articles}
    relevant_ids = primary_ids | supporting_ids

    found_primary_count = len(set(retrieved_ids) & primary_ids)
    relevant_retrieved_count = sum(
        article_id in relevant_ids for article_id in retrieved_ids
    )

    recall = found_primary_count / len(primary_ids)
    precision = (
        relevant_retrieved_count / len(retrieved_ids) if retrieved_ids else 0.0
    )

    return {
        "id_context_precision_at_5": precision,
        "id_context_recall_at_5": recall,
    }
