"""LangSmith 선택 문항 experiment 실행 스크립트 테스트"""

from pathlib import Path
from runpy import run_path
from types import SimpleNamespace

import pytest


SCRIPT = run_path(
    Path(__file__).resolve().parent.parent / "scripts" / "run_rag_evaluation.py"
)
DATASET_NAME = SCRIPT["DATASET_NAME"]
find_dataset_example = SCRIPT["find_dataset_example"]
run_full_dataset_experiment = SCRIPT["run_full_dataset_experiment"]
run_selected_questions_experiment = SCRIPT["run_selected_questions_experiment"]


class FakeClient:
    """질문 ID별 Dataset example 조회 기록"""

    def __init__(self, examples: list) -> None:
        self.examples = examples
        self.list_examples_kwargs = None

    def list_examples(self, **kwargs):
        self.list_examples_kwargs = kwargs
        return iter(self.examples)


def test_find_dataset_example_filters_by_question_id() -> None:
    """Dataset 이름과 질문 ID로 example 하나 조회"""
    example = SimpleNamespace(id="example-id")
    client = FakeClient([example])

    result = find_dataset_example(client, "A1")

    assert result is example
    assert client.list_examples_kwargs == {
        "dataset_name": DATASET_NAME,
        "metadata": {"question_id": "A1"},
        "limit": 2,
    }


def test_find_dataset_example_requires_exactly_one_match() -> None:
    """누락되거나 중복된 질문 ID 실행 방지"""
    with pytest.raises(ValueError, match="1개여야 합니다"):
        find_dataset_example(FakeClient([]), "missing")


def test_run_selected_questions_experiment_uses_one_worker() -> None:
    """선택한 example과 evaluator를 동시성 1로 실행"""
    examples = [SimpleNamespace(id="example-1"), SimpleNamespace(id="example-2")]
    client = FakeClient(examples)
    target = lambda inputs: inputs
    captured = {}

    def fake_evaluate(received_target, **kwargs):
        captured["target"] = received_target
        captured.update(kwargs)
        return "experiment-results"

    result = run_selected_questions_experiment(
        client=client,
        target=target,
        question_ids=["A1", "A2"],
        examples=examples,
        faithfulness_evaluator="faithfulness-evaluator",
        evaluate_fn=fake_evaluate,
    )

    assert result == "experiment-results"
    assert captured["target"] is target
    assert captured["data"] == examples
    assert captured["max_concurrency"] == 1
    assert captured["client"] is client
    assert captured["metadata"]["question_ids"] == ["A1", "A2"]
    assert captured["evaluators"][1] == "faithfulness-evaluator"
    assert len(captured["evaluators"]) == 2


def test_run_full_dataset_experiment_uses_registered_dataset() -> None:
    """Dataset 이름으로 전체 문항을 동시성 1로 실행"""
    client = FakeClient([])
    target = lambda inputs: inputs
    captured = {}

    def fake_evaluate(received_target, **kwargs):
        captured["target"] = received_target
        captured.update(kwargs)
        return "experiment-results"

    result = run_full_dataset_experiment(
        client=client,
        target=target,
        faithfulness_evaluator="faithfulness-evaluator",
        evaluate_fn=fake_evaluate,
    )

    assert result == "experiment-results"
    assert captured["target"] is target
    assert captured["data"] == DATASET_NAME
    assert captured["max_concurrency"] == 1
    assert captured["client"] is client
    assert "question_id" not in captured["metadata"]
    assert captured["evaluators"][1] == "faithfulness-evaluator"
    assert len(captured["evaluators"]) == 2
