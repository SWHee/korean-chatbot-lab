"""법령 RAG 체인 단위 테스트"""

import chatbot.rag as rag_module


class FakeGenerator:
    """전달받은 prompt를 기록하는 테스트 생성기"""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "예금은 관련 법령에 따라 보호됩니다."

    def stream(self, prompt: str):
        self.prompts.append(prompt)
        yield "예금은 "
        yield "1억원까지 보호됩니다."


def test_format_context_includes_source_and_text() -> None:
    """검색 조문의 출처와 본문을 모델 입력 문맥으로 변환"""
    articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "text": "보험금 한도는 1억원",
        },
        {
            "law_name": "예금자보호법",
            "article_no": "제32조",
            "effective_date": "20260102",
            "text": "보험금 지급 기준",
        },
    ]

    context = rag_module.format_context(articles)

    assert context == (
        "출처: 예금자보호법 시행령 제18조 (시행일: 20250901)\n"
        "보험금 한도는 1억원\n\n"
        "출처: 예금자보호법 제32조 (시행일: 20260102)\n"
        "보험금 지급 기준"
    )


def test_rag_prompt_formats_question_and_context() -> None:
    """질문과 법령 문맥을 system·human 메시지로 변환"""
    prompt_value = rag_module.RAG_PROMPT.invoke(
        {
            "question": "예금은 얼마까지 보호되나요?",
            "context": "출처: 예금자보호법 시행령 제18조\n보험금 한도는 1억원",
        }
    )
    messages = prompt_value.to_messages()

    assert "제공된 법령 근거만 사용" in messages[0].content
    assert messages[1].content == (
        "질문:\n예금은 얼마까지 보호되나요?\n\n"
        "법령 근거:\n출처: 예금자보호법 시행령 제18조\n보험금 한도는 1억원"
    )


def test_model_runnable_passes_rendered_prompt_to_generator() -> None:
    """LangChain prompt를 기존 Generator 입력 문자열로 연결"""
    generator = FakeGenerator()
    model = rag_module.create_model_runnable(generator)
    prompt_value = rag_module.RAG_PROMPT.invoke(
        {
            "question": "예금은 얼마까지 보호되나요?",
            "context": "예금자보호법 시행령 제18조: 보험금 한도는 1억원",
        }
    )

    answer = model.invoke(prompt_value)

    assert answer == "예금은 관련 법령에 따라 보호됩니다."
    assert "예금은 얼마까지 보호되나요?" in generator.prompts[0]
    assert "보험금 한도는 1억원" in generator.prompts[0]


def test_output_parser_returns_answer_text() -> None:
    """Generator 출력 문자열을 최종 답변 문자열로 변환"""
    answer = rag_module.OUTPUT_PARSER.invoke(
        "예금은 관련 법령에 따라 보호됩니다."
    )

    assert answer == "예금은 관련 법령에 따라 보호됩니다."


def test_rag_chain_connects_prompt_model_and_parser() -> None:
    """prompt·model·parser를 하나의 LCEL 체인으로 연결"""
    generator = FakeGenerator()
    chain = rag_module.create_rag_chain(generator)

    answer = chain.invoke(
        {
            "question": "예금은 얼마까지 보호되나요?",
            "context": "예금자보호법 시행령 제18조: 보험금 한도는 1억원",
        }
    )

    assert answer == "예금은 관련 법령에 따라 보호됩니다."
    assert "예금은 얼마까지 보호되나요?" in generator.prompts[0]
    assert "보험금 한도는 1억원" in generator.prompts[0]


def test_answer_question_invokes_chain_with_articles() -> None:
    """검색 조문 목록으로 RAG 답변 생성"""
    generator = FakeGenerator()
    articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "text": "보험금 한도는 1억원",
        }
    ]

    answer = rag_module.answer_question(
        generator, "예금은 얼마까지 보호되나요?", articles
    )

    assert answer == "예금은 관련 법령에 따라 보호됩니다."
    assert "예금은 얼마까지 보호되나요?" in generator.prompts[0]
    assert "예금자보호법 시행령 제18조" in generator.prompts[0]


def test_answer_with_retrieval_searches_articles_then_answers(monkeypatch) -> None:
    """질문 검색 결과로 RAG 답변 생성"""
    generator = FakeGenerator()
    calls = {}

    def fake_retrieve_articles(encoder, collection, question, top_k):
        calls["encoder"] = encoder
        calls["collection"] = collection
        calls["question"] = question
        calls["top_k"] = top_k
        return [
            {
                "law_name": "예금자보호법 시행령",
                "article_no": "제18조",
                "effective_date": "20250901",
                "text": "보험금 한도는 1억원",
            }
        ]

    monkeypatch.setattr(rag_module, "retrieve_articles", fake_retrieve_articles)

    encoder = object()
    collection = object()
    answer = rag_module.answer_with_retrieval(
        generator,
        encoder,
        collection,
        "예금은 얼마까지 보호되나요?",
        top_k=3,
    )

    assert answer == "예금은 관련 법령에 따라 보호됩니다."
    assert calls == {
        "encoder": encoder,
        "collection": collection,
        "question": "예금은 얼마까지 보호되나요?",
        "top_k": 3,
    }
    assert "보험금 한도는 1억원" in generator.prompts[0]


def test_stream_answer_question_streams_with_articles() -> None:
    """검색 조문 목록으로 RAG 답변 조각 생성"""
    generator = FakeGenerator()
    articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "text": "보험금 한도는 1억원",
        }
    ]

    chunks = list(
        rag_module.stream_answer_question(
            generator, "예금은 얼마까지 보호되나요?", articles
        )
    )

    assert chunks == ["예금은 ", "1억원까지 보호됩니다."]
    assert "예금은 얼마까지 보호되나요?" in generator.prompts[0]
    assert "예금자보호법 시행령 제18조" in generator.prompts[0]
