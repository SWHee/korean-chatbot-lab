"""법령 검색과 생성 모델을 연결하는 RAG 체인"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles


RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "예·적금 소비자보호 법령 안내자로서 제공된 법령 근거만 사용해 "
            "답변하세요. 근거가 부족하면 확인할 수 없다고 밝히고, 답변에는 "
            "법령명·조문번호·시행일을 명시하세요. 개별 상품의 보호 여부는 "
            "단정하지 마세요.",
        ),
        ("human", "질문:\n{question}\n\n법령 근거:\n{context}"),
    ]
)
OUTPUT_PARSER = StrOutputParser()


def format_context(articles: list[dict]) -> str:
    """검색 조문의 출처와 본문을 합친 모델 입력 문맥"""
    blocks = (
        f"출처: {article['law_name']} {article['article_no']} "
        f"(시행일: {article['effective_date']})\n{article['text']}"
        for article in articles
    )
    return "\n\n".join(blocks)


def build_rag_inputs(question: str, articles: list[dict]) -> dict[str, str]:
    """일괄·스트리밍 생성이 공유하는 question·context 입력"""
    return {
        "question": question,
        "context": format_context(articles),
    }


def create_model_runnable(generator) -> RunnableLambda:
    """프로젝트 Generator를 LCEL model 단계로 연결한 Runnable"""

    def generate_from_prompt(prompt_value) -> str:
        prompt_text = prompt_value.to_string()
        return generator.generate(prompt_text)

    return RunnableLambda(generate_from_prompt)


def create_rag_chain(generator) -> Runnable:
    """prompt·model·parser를 연결한 LCEL 체인"""
    prompt = RAG_PROMPT
    model = create_model_runnable(generator)
    parser = OUTPUT_PARSER

    return prompt | model | parser


def answer_question(generator, question: str, articles: list[dict]) -> str:
    """검색 조문 목록 기반 RAG 답변"""
    chain = create_rag_chain(generator)
    rag_inputs = build_rag_inputs(
        question=question,
        articles=articles,
    )
    return chain.invoke(rag_inputs)


def stream_answer_question(generator, question: str, articles: list[dict]):
    """검색 조문 목록 기반 RAG 답변 조각"""
    rag_inputs = build_rag_inputs(
        question=question,
        articles=articles,
    )
    prompt_value = RAG_PROMPT.invoke(rag_inputs)
    prompt_text = prompt_value.to_string()

    return generator.stream(prompt_text)


def answer_with_retrieval(
    generator,
    encoder,
    collection,
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    """검색과 답변 생성을 연결한 RAG 실행"""
    articles = retrieve_articles(
        encoder=encoder,
        collection=collection,
        question=question,
        top_k=top_k,
    )
    return answer_question(
        generator=generator,
        question=question,
        articles=articles,
    )
