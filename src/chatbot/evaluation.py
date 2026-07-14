"""현재 법령 RAG를 Dataset 평가에서 실행하는 함수"""

from chatbot.rag import answer_question, format_context
from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles


def run_rag_evaluation(
    inputs: dict[str, str],
    *,
    generator,
    encoder,
    collection,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, object]:
    """질문 하나의 RAG 답변·출처·검색 문맥 반환"""
    question = inputs["question"]   # 입력 단계
    articles = retrieve_articles(   # 검색 단계
        encoder=encoder,
        collection=collection,
        question=question,
        top_k=top_k,
    )
    answer = answer_question(   # 생성 단계
        generator=generator,
        question=question,
        articles=articles,
    )

    sources = [     # 메타데이터 정형화 단계
        {
            "law_name": article["law_name"],
            "article_no": article["article_no"],
            "effective_date": article["effective_date"],
            "similarity": article["similarity"],
        }
        for article in articles
    ]
    retrieved_contexts = [format_context([article]) for article in articles]    # 텍스트 형태로 포매팅 단계

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_contexts": retrieved_contexts,
    }
