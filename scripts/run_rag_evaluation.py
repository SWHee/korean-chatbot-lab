"""LangSmith에서 현재 법령 RAG의 한 문항 experiment 실행"""

import argparse
from collections.abc import Callable
from pathlib import Path

from langsmith import Client, evaluate

from chatbot.embedding import load_encoder
from chatbot.evaluation import (
    CORPUS_SNAPSHOT,
    DATASET_NAME,
    DATASET_VERSION,
    run_rag_evaluation,
)
from chatbot.evaluators import langsmith_retrieval_evaluator
from chatbot.ollama_generator import OllamaGenerator
from chatbot.settings import load_local_env
from chatbot.vectorstore import open_collection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTION_ID = "A1"
EXPERIMENT_PREFIX = "rag-v1-single"


def find_dataset_example(client: Client, question_id: str):
    """질문 ID가 일치하는 LangSmith example 하나 조회"""
    examples = list(
        client.list_examples(
            dataset_name=DATASET_NAME,
            metadata={"question_id": question_id},
            limit=2,
        )
    )
    if len(examples) != 1:
        raise ValueError(
            f"질문 ID {question_id!r}의 example은 1개여야 합니다: {len(examples)}개"
        )
    return examples[0]


def create_evaluation_target(generator, encoder, collection) -> Callable:
    """현재 RAG 자원을 LangSmith가 호출할 평가 함수로 연결"""

    def target(inputs: dict[str, str]) -> dict[str, object]:
        return run_rag_evaluation(
            inputs,
            generator=generator,
            encoder=encoder,
            collection=collection,
        )

    return target


def run_single_question_experiment(
    client: Client,
    target: Callable,
    question_id: str,
    evaluate_fn: Callable = evaluate,
):
    """Dataset 한 문항을 실행하고 검색 평가 점수 업로드"""
    example = find_dataset_example(client, question_id)
    return evaluate_fn(
        target,
        data=[example],
        evaluators=[langsmith_retrieval_evaluator],
        metadata={
            "dataset": DATASET_VERSION,
            "corpus_snapshot": CORPUS_SNAPSHOT,
            "question_id": question_id,
        },
        experiment_prefix=EXPERIMENT_PREFIX,
        max_concurrency=1,
        client=client,
    )


def parse_args() -> argparse.Namespace:
    """실행할 Dataset 질문 ID 입력"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-id", default=DEFAULT_QUESTION_ID)
    return parser.parse_args()


def main() -> None:
    """로컬 RAG 자원 준비 후 한 문항 experiment 실행"""
    args = parse_args()
    load_local_env(PROJECT_ROOT / ".env")
    client = Client()

    # 잘못된 질문 ID는 모델을 적재하기 전에 확인
    find_dataset_example(client, args.question_id)

    target = create_evaluation_target(
        generator=OllamaGenerator(),
        encoder=load_encoder(),
        collection=open_collection(),
    )
    results = run_single_question_experiment(
        client=client,
        target=target,
        question_id=args.question_id,
    )

    print(f"Experiment: {results.experiment_name}")
    if results.url:
        print(f"LangSmith: {results.url}")


if __name__ == "__main__":
    main()
