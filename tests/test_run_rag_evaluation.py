"""LangSmith 선택 문항 experiment 실행 스크립트 테스트"""

from pathlib import Path
from runpy import run_path
from types import SimpleNamespace

import pytest


SCRIPT = run_path(
    Path(__file__).resolve().parent.parent / "scripts" / "run_rag_evaluation.py"
)
DATASET_NAME = SCRIPT["DATASET_NAME"]
create_graph_evaluation_target = SCRIPT["create_graph_evaluation_target"]
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


class FakeRagGraph:
    """질문 입력과 고정 graph state 반환"""

    def __init__(self, result: dict) -> None:
        self.result = result
        self.received_state = None

    def invoke(self, state: dict) -> dict:
        self.received_state = state
        return self.result


def test_create_graph_evaluation_target_formats_graph_result() -> None:
    """그래프 상태를 기존 LangSmith evaluator 출력 계약으로 변환"""
    article = {
        "law_name": "예금자보호법",
        "article_no": "제32조",
        "effective_date": "20260102",
        "similarity": 0.9,
        "text": "보험금의 계산 기준",
    }
    graph = FakeRagGraph(
        {
            "question": "예금은 얼마까지 보호되나요?",
            "articles": [article],
            "answer": "법령 근거에 따른 답변",
        }
    )
    target = create_graph_evaluation_target(graph)

    result = target({"question": "예금은 얼마까지 보호되나요?"})

    assert graph.received_state == {"question": "예금은 얼마까지 보호되나요?"}
    assert result["answer"] == "법령 근거에 따른 답변"
    assert result["sources"] == [
        {
            "law_name": "예금자보호법",
            "article_no": "제32조",
            "effective_date": "20260102",
            "similarity": 0.9,
        }
    ]
    assert result["retrieved_contexts"] == [
        "[S1] 출처: 예금자보호법 제32조 (시행일: 20260102)\n"
        "보험금의 계산 기준"
    ]


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
    assert captured["metadata"]["pipeline"] == "langgraph-v1"
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
    assert captured["metadata"]["pipeline"] == "langgraph-v1"
    assert captured["evaluators"][1] == "faithfulness-evaluator"
    assert len(captured["evaluators"]) == 2
