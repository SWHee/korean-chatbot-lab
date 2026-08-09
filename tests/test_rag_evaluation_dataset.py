"""RAG 평가 Dataset 구조와 정답 조문 검증"""

import json
from pathlib import Path

from chatbot.law.statutes import parse_law


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "rag-v1-dev.jsonl"
LAWS_DIR = PROJECT_ROOT / "data" / "laws"

EXPECTED_CATEGORY_COUNTS = {
    "A": 12,
    "B": 3,
    "C": 3,
    "D": 4,
    "E": 2,
}
RETRIEVAL_METRICS = {"context_precision", "context_recall", "faithfulness"}


def load_examples() -> list[dict]:
    """JSONL Dataset 예시 목록"""
    return [
        json.loads(line)
        for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_dataset_has_expected_ids_and_categories() -> None:
    """24개 질문 ID와 유형별 개수 유지"""
    examples = load_examples()
    ids = [example["id"] for example in examples]

    assert len(examples) == 24
    assert len(ids) == len(set(ids))

    actual_counts = {
        category: sum(question_id.startswith(category) for question_id in ids)
        for category in EXPECTED_CATEGORY_COUNTS
    }
    assert actual_counts == EXPECTED_CATEGORY_COUNTS


def test_dataset_metric_contract_matches_retrieval_eligibility() -> None:
    """정답 조문 존재 여부와 지표 적용 범위 일치"""
    examples = load_examples()
    retrieval_examples = [
        example for example in examples if example["retrieval_eligible"]
    ]

    assert len(retrieval_examples) == 15

    for example in examples:
        enabled_metrics = {
            name
            for name, enabled in example["metric_eligibility"].items()
            if enabled
        }
        assert "answer_relevancy" in enabled_metrics
        assert bool(example["required_articles"]) == example["retrieval_eligible"]

        if example["retrieval_eligible"]:
            assert RETRIEVAL_METRICS <= enabled_metrics
        else:
            assert RETRIEVAL_METRICS.isdisjoint(enabled_metrics)


def test_dataset_answer_articles_exist_in_law_snapshot() -> None:
    """정답 법령명·조문번호가 XML snapshot에 존재"""
    known_articles = {
        (article.law_name, article.article_no)
        for path in LAWS_DIR.glob("*.xml")
        for article in parse_law(path)
    }

    for example in load_examples():
        answer_articles = (
            example["required_articles"]
            + example["supporting_articles"]
        )
        for article in answer_articles:
            key = (article["law_name"], article["article_no"])
            assert key in known_articles, f"{example['id']} 정답 조문 누락: {key}"


def test_dataset_examples_have_answer_rubric() -> None:
    """생성 품질 평가에 필요한 기준 존재"""
    for example in load_examples():
        assert example["split"] == "dev"
        assert example["question"].strip()
        assert example["reference_answer"].strip()
        assert example["required_claims"]
        assert example["forbidden_claims"]
        assert example["expected_behavior"].strip()
        assert example["corpus_snapshot"] == "2026-07-06"
        if "evaluation_note" in example:
            assert example["evaluation_note"].strip()
