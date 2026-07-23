"""LangSmith에서 LangGraph 법령 RAG experiment 실행"""

import argparse
from collections.abc import Callable
from pathlib import Path

from langsmith import Client, evaluate

from chatbot.embedding import load_encoder
from chatbot.evaluation import (
    CORPUS_SNAPSHOT,
    DATASET_NAME,
    DATASET_VERSION,
)
from chatbot.evaluators import (
    JUDGE_MODEL_NAME,
    create_faithfulness_evaluator,
    langsmith_retrieval_evaluator,
)
from chatbot.graph import create_rag_graph
from chatbot.ollama_generator import OllamaGenerator
from chatbot.rag import format_context
from chatbot.settings import load_local_env
from chatbot.vectorstore import open_collection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTION_ID = "A1"
BATCH_EXPERIMENT_PREFIX = "rag-graph-v1-batch"
FULL_EXPERIMENT_PREFIX = "rag-graph-v1-baseline"


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


def create_graph_evaluation_target(rag_graph) -> Callable:
    """LangGraph 실행 결과를 LangSmith 평가 출력으로 변환"""

    def target(inputs: dict[str, str]) -> dict[str, object]:
        graph_result = rag_graph.invoke({"question": inputs["question"]})
        answer = graph_result["answer"]
        articles = graph_result["articles"]

        sources = [
            {
                "law_name": article["law_name"],
                "article_no": article["article_no"],
                "effective_date": article["effective_date"],
                "similarity": article["similarity"],
            }
            for article in articles
        ]
        retrieved_contexts = [format_context([article]) for article in articles]

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_contexts": retrieved_contexts,
        }

    return target


def run_selected_questions_experiment(
    client: Client,
    target: Callable,
    question_ids: list[str],
    examples: list,
    faithfulness_evaluator,
    evaluate_fn: Callable = evaluate,
):
    """선택한 Dataset 문항을 한 요청씩 평가"""
    return evaluate_fn(
        target,
        data=examples,
        evaluators=[langsmith_retrieval_evaluator, faithfulness_evaluator],
        metadata={
            "dataset": DATASET_VERSION,
            "corpus_snapshot": CORPUS_SNAPSHOT,
            "question_ids": question_ids,
            "judge_model": JUDGE_MODEL_NAME,
            "pipeline": "langgraph-v1",
        },
        experiment_prefix=BATCH_EXPERIMENT_PREFIX,
        max_concurrency=1,
        client=client,
    )


def run_full_dataset_experiment(
    client: Client,
    target: Callable,
    faithfulness_evaluator,
    evaluate_fn: Callable = evaluate,
):
    """Dataset 전체 문항을 한 요청씩 실행하고 검색·답변 점수 업로드"""
    return evaluate_fn(
        target,
        data=DATASET_NAME,
        evaluators=[langsmith_retrieval_evaluator, faithfulness_evaluator],
        metadata={
            "dataset": DATASET_VERSION,
            "corpus_snapshot": CORPUS_SNAPSHOT,
            "judge_model": JUDGE_MODEL_NAME,
            "pipeline": "langgraph-v1",
        },
        experiment_prefix=FULL_EXPERIMENT_PREFIX,
        max_concurrency=1,
        client=client,
    )


def parse_args() -> argparse.Namespace:
    """실행할 Dataset 질문 ID 입력"""
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--question-ids",
        nargs="+",
        help="순차 실행할 Dataset 질문 ID 목록",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        help="등록된 Dataset 24문항 전체 실행",
    )
    return parser.parse_args()


def main() -> None:
    """로컬 RAG 그래프 준비 후 선택 문항 또는 전체 Dataset 실행"""
    args = parse_args()
    load_local_env(PROJECT_ROOT / ".env")
    client = Client()
    faithfulness_evaluator = create_faithfulness_evaluator()
    question_ids = args.question_ids or [DEFAULT_QUESTION_ID]
    examples = []

    if not args.all:
        # 잘못된 질문 ID는 모델을 적재하기 전에 확인
        examples = [
            find_dataset_example(client, question_id) for question_id in question_ids
        ]

    generator = OllamaGenerator()
    encoder = load_encoder()
    collection = open_collection()
    rag_graph = create_rag_graph(
        generator=generator,
        encoder=encoder,
        collection=collection,
    )
    target = create_graph_evaluation_target(rag_graph)

    if args.all:
        results = run_full_dataset_experiment(
            client=client,
            target=target,
            faithfulness_evaluator=faithfulness_evaluator,
        )
    else:
        results = run_selected_questions_experiment(
            client=client,
            target=target,
            question_ids=question_ids,
            examples=examples,
            faithfulness_evaluator=faithfulness_evaluator,
        )

    print(f"Experiment: {results.experiment_name}")
    if results.url:
        print(f"LangSmith: {results.url}")


if __name__ == "__main__":
    main()
