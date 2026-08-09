"""Chroma 검색 결과와 브루트포스 정확 검색의 일치 검증 (ADR 0006 근거).

사용법: uv run python scripts/verify_index.py
현재 RAG Dataset의 검색 평가 대상 문항에서 조문 단위 top-5를 확인한다.
"""

import json
from pathlib import Path

import torch

from chatbot.evaluation.rag_dataset import DATASET_VERSION
from chatbot.law.embedding import load_encoder
from chatbot.law.vectorstore import open_collection, search


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "rag-v1-dev.jsonl"


def load_retrieval_cases(
    path: Path = DATASET_PATH,
) -> list[tuple[str, str, set[tuple[str, str]]]]:
    """현재 RAG Dataset의 검색 평가 대상 질문과 필수 조문"""
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [
        (
            row["id"],
            row["question"],
            {
                (article["law_name"], article["article_no"])
                for article in row["required_articles"]
            },
        )
        for row in rows
        if row["retrieval_eligible"]
    ]


def article_top5(scores: dict) -> list:
    """(법령명, 조문번호)별 최고 점수 기준 상위 5개"""
    return sorted(scores, key=scores.get, reverse=True)[:5]


def main() -> None:
    cases = load_retrieval_cases()
    print("검색 평가 Dataset:", DATASET_VERSION)
    collection = open_collection()
    print("컬렉션 청크 수:", collection.count())

    stored = collection.get(include=["embeddings", "metadatas"])
    embeddings = torch.tensor(stored["embeddings"], dtype=torch.float32)
    keys = [(m["law_name"], m["article_no"]) for m in stored["metadatas"]]

    encoder = load_encoder()
    query_embeddings = torch.tensor(
        encoder.encode([q for _, q, _ in cases], batch_size=16,
                       normalize_embeddings=True)
    )

    mismatch = 0
    answer_hit5 = 0
    for qi, (qid, _, answer_articles) in enumerate(cases):
        sims = query_embeddings[qi] @ embeddings.T
        brute = {}
        for ci, key in enumerate(keys):
            s = sims[ci].item()
            if s > brute.get(key, -2.0):
                brute[key] = s

        hits = search(collection, query_embeddings[qi].tolist(), top_k=50)
        chroma = {}
        for h in hits:
            key = (h["law_name"], h["article_no"])
            if h["similarity"] > chroma.get(key, -2.0):
                chroma[key] = h["similarity"]

        bf5, ch5 = article_top5(brute), article_top5(chroma)
        if bf5 != ch5:
            mismatch += 1
            print(f"{qid} 불일치!\n  브루트포스: {bf5}\n  Chroma:    {ch5}")
        answer_hit5 += bool(set(ch5) & answer_articles)

    total = len(cases)
    print(f"top-5 조문 완전 일치: {total - mismatch}/{total}")
    print(f"Chroma 기준 Hit@5: {answer_hit5}/{total}")


if __name__ == "__main__":
    main()
