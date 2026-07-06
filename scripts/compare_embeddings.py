"""임베딩 모델 4종 비교 재현 스크립트 (ADR 0005 근거 실험).

사용법: uv run python scripts/compare_embeddings.py
측정: 조문 단위 Hit@1/3/5, Recall@1/3/5, MRR + 토큰 분포 + 실행 시간
gold 라벨은 2026-07-06 법령 원문 대조로 확정 (docs/evaluation/rag-questions.md)
"""

import json
import time
from pathlib import Path

import torch
from sentence_transformers import SentenceTransformer

from chatbot.chunking import chunk_articles
from chatbot.statutes import parse_law

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "laws"

FSC = "금융소비자 보호에 관한 법률"
FSCD = "금융소비자 보호에 관한 법률 시행령"
DPA = "예금자보호법"
DPAD = "예금자보호법 시행령"

# (질문ID, 질문, gold 조문 집합)
QUESTIONS = [
    ("A1", "은행이 파산하면 내 예금은 얼마까지 보호받나요?", {(DPA, "제32조"), (DPAD, "제18조")}),
    ("A2", "보호 한도 1억원은 원금 기준인가요, 이자 포함인가요?", {(DPA, "제32조"), (DPA, "제2조")}),
    ("A3", "여러 은행에 예금을 나눠 두면 각각 보호받나요?", {(DPA, "제32조"), (DPAD, "제18조")}),
    ("A4", "적금도 예금자보호 대상인가요?", {(DPA, "제2조")}),
    ("A6", "저축은행 예금도 은행과 같은 한도로 보호되나요?", {(DPA, "제2조")}),
    ("A7", "은행이 예금 상품을 팔 때 무엇을 설명할 의무가 있나요?", {(FSC, "제19조"), (FSCD, "제13조")}),
    ("A8", "금소법에서 예금은 어떤 상품 유형으로 분류되나요?", {(FSC, "제3조")}),
    ("A9", "은행이 대출을 조건으로 적금 가입을 강요하면 불법인가요?", {(FSC, "제20조")}),
    ("A10", "금융상품 광고에는 어떤 규제가 있나요?", {(FSC, "제22조")}),
    ("A11", "설명을 제대로 못 받고 가입했다면 어떤 권리가 있나요?", {(FSC, "제47조"), (FSC, "제44조")}),
    ("A12", "예금보험료는 예금자가 내는 건가요?", {(DPA, "제30조")}),
    ("B1", "예금자보호 한도가 1억원으로 오른 게 언제부터인가요?", {(DPAD, "제18조")}),
    ("C1", "예금도 14일 안에 청약철회하면 되죠?", {(FSC, "제46조")}),
    ("C2", "은행이 망하면 정부가 세금으로 전액 보상해 주는 거죠?", {(DPA, "제32조")}),
    ("C3", "예금자보호는 5천만원까지라던데요?", {(DPAD, "제18조")}),
]
# retrieval 평가 제외와 사유:
#   A5 — '외화'가 현행 조문 문면에 없음 (예금등 정의의 해석 영역)
#   B2 — 보험사고 시점 기준 경과규정은 부칙 영역, 현행 조문단위에 없음
#   B3 — 종전 한도 5천만원은 현행 조문에 없음 (벌금·보증금 조항만 검색됨)

MODELS = [
    ("intfloat/multilingual-e5-large", "e5"),
    ("BAAI/bge-m3", None),
    ("nlpai-lab/KURE-v1", None),
    ("Qwen/Qwen3-Embedding-0.6B", "qwen"),
]


def main() -> None:
    articles = []
    for f in sorted(DATA_DIR.glob("*.xml")):
        articles += parse_law(f)
    chunks = chunk_articles(articles)
    gold_all = {g for _, _, gs in QUESTIONS for g in gs}
    known = {(c.law_name, c.article_no) for c in chunks}
    assert gold_all <= known, f"gold 누락: {gold_all - known}"
    print(f"청크 {len(chunks)}개, 평가 질문 {len(QUESTIONS)}개", flush=True)

    results = {}
    for model_name, style in MODELS:
        model = SentenceTransformer(model_name, device="mps")
        tok = model.tokenizer
        tlens = sorted(len(tok(c.text)["input_ids"]) for c in chunks)
        tstat = {"max": tlens[-1], "p90": tlens[int(len(tlens) * 0.9)],
                 "over512": sum(t > 512 for t in tlens)}

        doc_texts = [("passage: " + c.text) if style == "e5" else c.text for c in chunks]
        q_texts = [("query: " + q) if style == "e5" else q for _, q, _ in QUESTIONS]

        t0 = time.time()
        doc_emb = model.encode(doc_texts, batch_size=16, normalize_embeddings=True,
                               convert_to_tensor=True, show_progress_bar=False)
        index_s = time.time() - t0
        q_kwargs = {"prompt_name": "query"} if style == "qwen" else {}
        q_emb = model.encode(q_texts, normalize_embeddings=True,
                             convert_to_tensor=True, show_progress_bar=False, **q_kwargs)

        sims = q_emb @ doc_emb.T  # 정규화 벡터라 내적=코사인
        keys = [(c.law_name, c.article_no) for c in chunks]
        metrics = {k: 0.0 for k in ["hit1", "hit3", "hit5", "rec1", "rec3", "rec5", "mrr"]}
        per_q = {}
        for qi, (qid, _, gold) in enumerate(QUESTIONS):
            best = {}  # 조문 단위 집계: 자식 청크 중 최고 점수
            for ci, key in enumerate(keys):
                s = sims[qi, ci].item()
                if s > best.get(key, -2.0):
                    best[key] = s
            ranked = sorted(best, key=best.get, reverse=True)
            for k in (1, 3, 5):
                topk = set(ranked[:k])
                metrics[f"hit{k}"] += bool(topk & gold)
                metrics[f"rec{k}"] += len(topk & gold) / len(gold)
            first = next(i for i, key in enumerate(ranked) if key in gold)
            metrics["mrr"] += 1 / (first + 1)
            per_q[qid] = first + 1
        nq = len(QUESTIONS)
        results[model_name] = {
            "metrics": {k: round(v / nq, 3) for k, v in metrics.items()},
            "tokens": tstat, "index_s": round(index_s, 1),
            "first_gold_rank": per_q,
        }
        print(model_name, json.dumps(results[model_name], ensure_ascii=False), flush=True)
        del model, doc_emb, q_emb, sims
        torch.mps.empty_cache()


if __name__ == "__main__":
    main()
