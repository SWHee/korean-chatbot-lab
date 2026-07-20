"""로컬 RAG 평가 JSONL을 LangSmith Dataset으로 등록"""

import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from langsmith import Client

from chatbot.evaluation import DATASET_NAME, DATASET_VERSION
from chatbot.settings import load_local_env


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "rag-v1-dev.jsonl"
DATASET_DESCRIPTION = "법령 RAG의 LangChain·LangGraph 전후 비교용 개발 Dataset"


def load_dataset_rows(path: Path = DATASET_PATH) -> list[dict]:
    """JSONL에서 평가 문항 목록 로드"""
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_langsmith_example(row: dict) -> dict:
    """평가 문항 하나를 LangSmith example 형식으로 변환"""
    rubric_excluded_keys = {
        "id",
        "split",
        "category",
        "question",
        "corpus_snapshot",
        "reference_answer",
    }
    rubric = {
        key: value for key, value in row.items() if key not in rubric_excluded_keys
    }

    return {
        "id": uuid5(NAMESPACE_URL, f"{DATASET_NAME}:{row['id']}"),
        "inputs": {"question": row["question"]},
        "outputs": {"reference_answer": row["reference_answer"]},
        "metadata": {
            "question_id": row["id"],
            "category": row["category"],
            "dataset_version": DATASET_VERSION,
            "corpus_snapshot": row["corpus_snapshot"],
            "rubric": rubric,
        },
        "split": row["split"],
    }


def register_dataset(client: Client, rows: list[dict]):
    """Dataset을 준비하고 고정 ID example을 생성·갱신"""
    dataset_exists = client.has_dataset(dataset_name=DATASET_NAME)
    if dataset_exists:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
    else:
        dataset = client.create_dataset(
            DATASET_NAME,
            description=DATASET_DESCRIPTION,
            metadata={"dataset_version": DATASET_VERSION},
        )

    examples = [build_langsmith_example(row) for row in rows]
    if dataset_exists:
        response = client.update_examples(dataset_id=dataset.id, updates=examples)
    else:
        response = client.create_examples(
            dataset_id=dataset.id,
            examples=examples,
            max_concurrency=1,
        )
    return dataset, response


def main() -> None:
    """환경 변수 로드 후 LangSmith Dataset 등록"""
    load_local_env(PROJECT_ROOT / ".env")
    rows = load_dataset_rows()
    dataset, response = register_dataset(Client(), rows)
    count = (
        response.get("count", len(rows))
        if isinstance(response, dict)
        else getattr(response, "count", len(rows))
    )
    print(f"Dataset: {dataset.name}")
    print(f"등록 문항: {count}개")


if __name__ == "__main__":
    main()
