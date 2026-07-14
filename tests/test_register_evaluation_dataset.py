"""LangSmith 평가 Dataset 등록 스크립트 테스트"""

from pathlib import Path
from runpy import run_path
from types import SimpleNamespace


SCRIPT = run_path(
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "register_evaluation_dataset.py"
)
DATASET_NAME = SCRIPT["DATASET_NAME"]
build_langsmith_example = SCRIPT["build_langsmith_example"]
load_dataset_rows = SCRIPT["load_dataset_rows"]
register_dataset = SCRIPT["register_dataset"]


class FakeClient:
    """네트워크 없이 Dataset 등록 호출 기록"""

    def __init__(self, dataset_exists: bool) -> None:
        self.dataset_exists = dataset_exists
        self.dataset = SimpleNamespace(id="dataset-id", name=DATASET_NAME)
        self.created_dataset = None
        self.created_examples = None

    def has_dataset(self, *, dataset_name: str) -> bool:
        assert dataset_name == DATASET_NAME
        return self.dataset_exists

    def read_dataset(self, *, dataset_name: str):
        assert dataset_name == DATASET_NAME
        return self.dataset

    def create_dataset(self, dataset_name: str, **kwargs):
        self.created_dataset = {"name": dataset_name, **kwargs}
        return self.dataset

    def create_examples(self, **kwargs):
        self.created_examples = kwargs
        return {"count": len(kwargs["examples"])}


def test_build_langsmith_example_separates_input_reference_and_metadata() -> None:
    """질문·정답 기준·식별 정보를 LangSmith 영역별로 분리"""
    row = load_dataset_rows()[0]

    example = build_langsmith_example(row)

    assert example["inputs"] == {"question": row["question"]}
    assert example["outputs"]["required_articles"] == row["required_articles"]
    assert example["metadata"] == {
        "question_id": "A1",
        "category": "legal_grounding",
        "dataset_version": "rag-v1-dev",
    }
    assert example["split"] == "dev"
    assert example["id"] == build_langsmith_example(row)["id"]


def test_register_dataset_creates_dataset_and_examples() -> None:
    """새 Dataset 생성 후 문항 일괄 등록"""
    client = FakeClient(dataset_exists=False)
    rows = load_dataset_rows()[:2]

    dataset, response = register_dataset(client, rows)

    assert dataset is client.dataset
    assert response == {"count": 2}
    assert client.created_dataset["name"] == DATASET_NAME
    assert client.created_examples["dataset_id"] == "dataset-id"
    assert len(client.created_examples["examples"]) == 2
    assert client.created_examples["max_concurrency"] == 1


def test_register_dataset_reuses_existing_dataset() -> None:
    """같은 이름의 Dataset 재사용"""
    client = FakeClient(dataset_exists=True)

    register_dataset(client, load_dataset_rows()[:1])

    assert client.created_dataset is None
    assert len(client.created_examples["examples"]) == 1
