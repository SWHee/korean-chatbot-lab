"""법령 검색과 생성 모델을 연결하는 RAG 체인"""

from collections.abc import Iterator
from typing import Annotated

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel, ConfigDict, Field

from chatbot.retriever import DEFAULT_TOP_K, retrieve_articles


INSUFFICIENT_EVIDENCE_MESSAGE = (
    "질문과 바로 연결되는 법령 근거를 찾지 못했어요.\n"
    "법령·소비자보호 기준이 궁금한지, 예금·적금 상품을 비교하고 싶은지 "
    "조금만 더 알려주시면 알맞게 다시 확인해 드릴게요.\n"
    "예: ‘예금자보호 한도가 궁금해요’ 또는 ‘12개월 정기예금을 비교해 주세요’\n"
    "상품별 금리와 가입 조건은 바뀔 수 있으니 최종 선택 전 금융회사의 "
    "최신 상품설명서도 함께 확인해 주세요."
)


class RagAnswer(BaseModel):
    """법령 근거 기반 구조화 답변"""

    model_config = ConfigDict(extra="forbid")

    can_answer: bool = Field(
        description="제공된 법령 근거로 질문에 직접 답할 수 있는지 여부"
    )
    answer: str = Field(
        description="답할 수 있을 때 고객에게 보여줄 쉬운 한국어 존댓말 설명"
    )
    source_ids: list[str] = Field(
        default_factory=list,
        max_length=DEFAULT_TOP_K,
        description="답변을 직접 뒷받침하는 법령 근거 ID",
    )


class RagStreamEnvelope(BaseModel):
    """근거를 답변보다 먼저 확정하는 스트리밍 전용 형식"""

    model_config = ConfigDict(extra="forbid")

    result: tuple[
        Annotated[
            bool,
            Field(description="법령 근거로 직접 답할 수 있는지"),
        ],
        Annotated[
            list[str],
            Field(
                max_length=DEFAULT_TOP_K,
                description="직접 근거가 되는 S번호 목록",
            ),
        ],
        Annotated[
            str,
            Field(description="고객에게 보여줄 한국어 존댓말 답변"),
        ],
    ] = Field(
        description="can_answer, source_ids, answer 순서의 결과",
    )


RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 예·적금 금융 상담 챗봇에서 법령 근거를 설명하는 담당자입니다.\n"
            "- 제공된 법령 근거만 사용하세요.\n"
            "- 질문에 직접 답하는 근거가 있으면 can_answer를 true로 하고, "
            "결론을 먼저 말한 뒤 필요한 이유와 조건을 친절한 한국어 존댓말로 "
            "설명하세요. 같은 내용은 반복하지 마세요.\n"
            "- 직접 답하는 근거가 없으면 can_answer를 false로 하고 answer와 "
            "source_ids를 비우세요.\n"
            "- source_ids에는 답변을 직접 뒷받침하는 제공된 [S번호]만 넣으세요.\n"
            "- 근거에 없는 내용을 추측하거나 개별 상품의 보호 여부를 단정하지 "
            "마세요.\n"
            "- 전달된 JSON schema에 맞는 JSON만 반환하세요.",
        ),
        # 사용자 질문과 검색 조문을 함께 전달
        ("human", "질문:\n{question}\n\n법령 근거:\n{context}"),
    ]
)


def format_context(articles: list[dict]) -> str:
    """검색 조문에 근거 ID를 붙인 모델 입력 문맥"""
    if not articles:
        return "검색된 법령 근거 없음"

    blocks = (
        f"[S{index}] 출처: {article['law_name']} {article['article_no']} "
        f"(시행일: {article['effective_date']})\n{article['text']}"
        for index, article in enumerate(articles, start=1)
    )
    return "\n\n".join(blocks)


def build_rag_inputs(question: str, articles: list[dict]) -> dict[str, str]:
    """일괄·스트리밍 생성이 공유하는 question·context 입력"""
    return {
        "question": question,
        "context": format_context(articles),
    }


def prompt_to_chat_messages(prompt_value) -> list[dict[str, str]]:
    """LangChain prompt를 역할별 Generator 메시지로 변환"""
    messages = []
    for message in prompt_value.to_messages():
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            raise TypeError(f"unsupported chat message: {type(message).__name__}")

        if not isinstance(message.content, str):
            raise TypeError("chat message content must be a string")
        messages.append({"role": role, "content": message.content})
    return messages


def create_model_runnable(generator) -> RunnableLambda:
    """프로젝트 Generator를 LCEL model 단계로 연결한 Runnable"""

    def generate_from_prompt(prompt_value) -> RagAnswer:
        return generator.generate_structured(
            messages=prompt_to_chat_messages(prompt_value),
            response_model=RagAnswer,
        )

    return RunnableLambda(generate_from_prompt)


def create_rag_chain(generator) -> Runnable:
    """prompt와 구조화 model 단계를 연결한 LCEL 체인"""
    return RAG_PROMPT | create_model_runnable(generator)


def validate_rag_answer(answer: RagAnswer, articles: list[dict]) -> None:
    """답변 가능 여부와 실제 검색 근거 ID 조합 검증"""
    available_source_ids = {
        f"S{index}" for index in range(1, len(articles) + 1)
    }
    source_ids = set(answer.source_ids)

    if len(source_ids) != len(answer.source_ids):
        raise ValueError("source_ids must not contain duplicates")
    if not source_ids <= available_source_ids:
        raise ValueError("source_ids contain an unknown law source")
    if answer.can_answer:
        if not answer.answer.strip():
            raise ValueError("grounded answer text is required")
        if not source_ids:
            raise ValueError("grounded answer requires at least one source")
    elif answer.answer.strip() or source_ids:
        raise ValueError("unanswerable result must not contain answer or sources")


def render_rag_answer(answer: RagAnswer, articles: list[dict]) -> str:
    """검증된 구조화 답변을 사용자용 상담 문장으로 변환"""
    try:
        validate_rag_answer(answer, articles)
    except ValueError:
        return INSUFFICIENT_EVIDENCE_MESSAGE

    if not answer.can_answer:
        return INSUFFICIENT_EVIDENCE_MESSAGE

    article_by_id = {
        f"S{index}": article
        for index, article in enumerate(articles, start=1)
    }
    source_lines = []
    for source_id in answer.source_ids:
        article = article_by_id[source_id]
        source_lines.append(
            f"- {article['law_name']} {article['article_no']} "
            f"(시행일: {article['effective_date']})"
        )

    sections = [
        answer.answer.strip(),
        "확인한 법령 근거\n" + "\n".join(source_lines),
    ]

    return "\n\n".join(sections)


def answer_question(generator, question: str, articles: list[dict]) -> str:
    """검색 조문 목록 기반 구조화 RAG 답변"""
    chain = create_rag_chain(generator)
    rag_inputs = build_rag_inputs(
        question=question,
        articles=articles,
    )
    structured_answer = chain.invoke(rag_inputs)
    return render_rag_answer(structured_answer, articles)


def stream_answer_question(
    generator,
    question: str,
    articles: list[dict],
) -> Iterator[str]:
    """검증 가능한 구조화 답변 본문과 출처 순차 전달"""
    prompt_value = RAG_PROMPT.invoke(
        build_rag_inputs(
            question=question,
            articles=articles,
        )
    )
    structured_stream = generator.stream_structured(
        messages=[
            {
                **message,
                "content": (
                    message["content"]
                    + "\n- 스트리밍 응답의 result 배열은 반드시 "
                    "[can_answer, source_ids, answer] 순서로 채우세요."
                    if message["role"] == "system"
                    else message["content"]
                ),
            }
            for message in prompt_to_chat_messages(prompt_value)
        ],
        response_model=RagStreamEnvelope,
    )
    streamed_answer = ""

    while True:
        try:
            partial = next(structured_stream)
        except StopIteration as completed:  # 반복이 끝났음을 알리는 예외처리 StopIteration
            can_answer, source_ids, answer = completed.value.result
            structured_answer = RagAnswer(
                can_answer=can_answer,
                source_ids=source_ids,
                answer=answer,
            )
            break

        result = partial.get("result")
        if (
            isinstance(result, list)
            and result
            and result[0] is False
        ):
            structured_stream.close()
            yield from INSUFFICIENT_EVIDENCE_MESSAGE.splitlines(
                keepends=True
            )
            return

        if (
            not isinstance(result, list)
            or len(result) < 3
            or result[0] is not True
            or not isinstance(result[1], list)
            or not isinstance(result[2], str)
        ):
            continue

        visible_answer = result[2].strip()
        try:
            validate_rag_answer(
                RagAnswer(
                    can_answer=True,
                    source_ids=result[1],
                    answer=visible_answer,
                ),
                articles,
            )
        except (TypeError, ValueError):
            continue

        if not visible_answer.startswith(streamed_answer):
            continue
        new_text = visible_answer[len(streamed_answer) :]
        if new_text:
            streamed_answer = visible_answer
            yield new_text

    rendered_answer = render_rag_answer(structured_answer, articles)
    if not streamed_answer:
        yield from rendered_answer.splitlines(keepends=True)
        return

    if not rendered_answer.startswith(streamed_answer):
        raise ValueError("structured answer changed after streaming")
    remaining_text = rendered_answer[len(streamed_answer) :]
    if remaining_text:
        yield remaining_text


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
