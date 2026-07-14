"""RAG 평가 실행 함수 단위 테스트"""

import chatbot.evaluation as evaluation_module


def test_run_rag_evaluation_returns_answer_sources_and_contexts(monkeypatch) -> None:
    """질문 하나의 생성 답변과 평가용 검색 결과 반환"""
    retrieved_articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "similarity": 0.82,
            "text": "보험금 지급한도는 1억원",
        }
    ]
    calls = {}

    def fake_retrieve_articles(encoder, collection, question, top_k):
        calls["retrieval"] = {
            "encoder": encoder,
            "collection": collection,
            "question": question,
            "top_k": top_k,
        }
        return retrieved_articles

    def fake_answer_question(generator, question, articles):
        calls["generation"] = {
            "generator": generator,
            "question": question,
            "articles": articles,
        }
        return "예금은 1인당 1억원까지 보호됩니다."

    monkeypatch.setattr(
        evaluation_module,
        "retrieve_articles",
        fake_retrieve_articles,
    )
    monkeypatch.setattr(
        evaluation_module,
        "answer_question",
        fake_answer_question,
    )

    generator = object()
    encoder = object()
    collection = object()
    result = evaluation_module.run_rag_evaluation(
        {"question": "은행이 파산하면 내 예금은 얼마까지 보호받나요?"},
        generator=generator,
        encoder=encoder,
        collection=collection,
    )

    assert calls == {
        "retrieval": {
            "encoder": encoder,
            "collection": collection,
            "question": "은행이 파산하면 내 예금은 얼마까지 보호받나요?",
            "top_k": 5,
        },
        "generation": {
            "generator": generator,
            "question": "은행이 파산하면 내 예금은 얼마까지 보호받나요?",
            "articles": retrieved_articles,
        },
    }
    assert result == {
        "answer": "예금은 1인당 1억원까지 보호됩니다.",
        "sources": [
            {
                "law_name": "예금자보호법 시행령",
                "article_no": "제18조",
                "effective_date": "20250901",
                "similarity": 0.82,
            }
        ],
        "retrieved_contexts": [
            "출처: 예금자보호법 시행령 제18조 (시행일: 20250901)\n"
            "보험금 지급한도는 1억원"
        ],
    }
