"""법령 RAG 체인 단위 테스트"""

import chatbot.rag as rag_module


class FakeGenerator:
    """전달받은 chat messages를 기록하는 테스트 생성기"""

    def __init__(self, response: rag_module.RagAnswer | None = None) -> None:
        self.messages: list[list[dict[str, str]]] = []
        self.response = response or rag_module.RagAnswer(
            can_answer=True,
            answer="예금은 관련 법령에 따라 보호됩니다.",
            source_ids=["S1"],
        )

    def generate_structured(self, *, messages, response_model):
        self.messages.append(messages)
        assert response_model is rag_module.RagAnswer
        return self.response

    def stream_structured(self, *, messages, response_model):
        self.messages.append(messages)
        assert response_model is rag_module.RagStreamEnvelope
        if self.response.can_answer:
            midpoint = max(1, len(self.response.answer) // 2)
            for answer in (
                self.response.answer[:midpoint],
                self.response.answer,
            ):
                yield {
                    "result": [
                        True,
                        self.response.source_ids,
                        answer,
                    ]
                }
        else:
            yield {
                "result": [False, [], ""],
            }
        return rag_module.RagStreamEnvelope(
            result=(
                self.response.can_answer,
                self.response.source_ids,
                self.response.answer,
            )
        )


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
        "[S1] 출처: 예금자보호법 시행령 제18조 (시행일: 20250901)\n"
        "보험금 한도는 1억원\n\n"
        "[S2] 출처: 예금자보호법 제32조 (시행일: 20260102)\n"
        "보험금 지급 기준"
    )


def test_build_rag_inputs_combines_question_and_articles() -> None:
    """일괄·스트리밍 생성이 공유할 question·context 입력 구성"""
    articles = [
        {
            "law_name": "예금자보호법 시행령",
            "article_no": "제18조",
            "effective_date": "20250901",
            "text": "보험금 한도는 1억원",
        }
    ]

    inputs = rag_module.build_rag_inputs(
        "예금은 얼마까지 보호되나요?", articles
    )

    assert inputs == {
        "question": "예금은 얼마까지 보호되나요?",
        "context": (
            "[S1] 출처: 예금자보호법 시행령 제18조 (시행일: 20250901)\n"
            "보험금 한도는 1억원"
        ),
    }


def test_format_context_marks_missing_evidence() -> None:
    """검색 조문이 없음을 모델 입력에 명시"""
    assert rag_module.format_context([]) == "검색된 법령 근거 없음"


def test_rag_prompt_formats_question_and_context() -> None:
    """질문과 법령 문맥을 system·human 메시지로 변환"""
    prompt_value = rag_module.RAG_PROMPT.invoke(
        {
            "question": "예금은 얼마까지 보호되나요?",
            "context": "출처: 예금자보호법 시행령 제18조\n보험금 한도는 1억원",
        }
    )
    messages = prompt_value.to_messages()
    system_message = messages[0].content

    assert "제공된 법령 근거만 사용" in system_message
    assert "can_answer" in system_message
    assert "친절한 한국어 존댓말" in system_message
    assert "같은 내용은 반복하지 마세요" in system_message
    assert "제공된 [S번호]만" in system_message
    assert "근거에 없는 내용을 추측" in system_message
    assert "개별 상품의 보호 여부" in system_message
    assert messages[1].content == (
        "질문:\n예금은 얼마까지 보호되나요?\n\n"
        "법령 근거:\n출처: 예금자보호법 시행령 제18조\n보험금 한도는 1억원"
    )


def test_model_runnable_passes_chat_roles_to_generator() -> None:
    """LangChain system·human 역할을 구조화 Generator에 전달"""
    generator = FakeGenerator()
    model = rag_module.create_model_runnable(generator)
    prompt_value = rag_module.RAG_PROMPT.invoke(
        {
            "question": "예금은 얼마까지 보호되나요?",
            "context": "예금자보호법 시행령 제18조: 보험금 한도는 1억원",
        }
    )

    result = model.invoke(prompt_value)

    assert result == generator.response
    assert generator.messages[0][0]["role"] == "system"
    assert generator.messages[0][1]["role"] == "user"
    assert "예금은 얼마까지 보호되나요?" in generator.messages[0][1]["content"]
    assert "보험금 한도는 1억원" in generator.messages[0][1]["content"]


def test_rag_chain_returns_structured_answer() -> None:
    """prompt와 model을 구조화 응답 LCEL 체인으로 연결"""
    generator = FakeGenerator()
    chain = rag_module.create_rag_chain(generator)

    result = chain.invoke(
        {
            "question": "예금은 얼마까지 보호되나요?",
            "context": "예금자보호법 시행령 제18조: 보험금 한도는 1억원",
        }
    )

    assert result == generator.response


def test_answer_question_renders_answer_and_validated_source() -> None:
    """구조화 답변을 상담 문장과 실제 법령 출처로 렌더링"""
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

    assert answer == (
        "예금은 관련 법령에 따라 보호됩니다.\n\n"
        "확인한 법령 근거\n"
        "- 예금자보호법 시행령 제18조 (시행일: 20250901)"
    )
    assert "예금은 얼마까지 보호되나요?" in generator.messages[0][1]["content"]
    assert "예금자보호법 시행령 제18조" in generator.messages[0][1]["content"]


def test_answer_question_uses_fixed_message_when_evidence_is_insufficient() -> None:
    """근거 부족 상태에서는 모델 문장 대신 고정 안내 반환"""
    generator = FakeGenerator(
        rag_module.RagAnswer(
            can_answer=False,
            answer="이 상품에 가입하셔도 됩니다.",
            source_ids=[],
        )
    )

    answer = rag_module.answer_question(
        generator,
        "은행이 파산하면 얼마까지 보호되나요?",
        [],
    )

    assert answer == rag_module.INSUFFICIENT_EVIDENCE_MESSAGE


def test_render_rag_answer_falls_back_for_unknown_source_id() -> None:
    """검색되지 않은 법령 근거 ID를 사용자에게 노출하지 않음"""
    answer = rag_module.RagAnswer(
        can_answer=True,
        answer="예금은 보호됩니다.",
        source_ids=["S2"],
    )

    rendered = rag_module.render_rag_answer(
        answer,
        [{"law_name": "예금자보호법", "article_no": "제1조"}],
    )

    assert rendered == rag_module.INSUFFICIENT_EVIDENCE_MESSAGE


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

    assert answer == (
        "예금은 관련 법령에 따라 보호됩니다.\n\n"
        "확인한 법령 근거\n"
        "- 예금자보호법 시행령 제18조 (시행일: 20250901)"
    )
    assert calls == {
        "encoder": encoder,
        "collection": collection,
        "question": "예금은 얼마까지 보호되나요?",
        "top_k": 3,
    }
    assert "보험금 한도는 1억원" in generator.messages[0][1]["content"]


def test_stream_answer_question_yields_answer_chunks_and_validated_source() -> None:
    """구조화 답변 본문 조각과 검증된 출처 순차 전달"""
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

    assert len(chunks) > 1
    assert "".join(chunks) == (
        "예금은 관련 법령에 따라 보호됩니다.\n\n"
        "확인한 법령 근거\n"
        "- 예금자보호법 시행령 제18조 (시행일: 20250901)"
    )
    assert "예금은 얼마까지 보호되나요?" in generator.messages[0][1]["content"]
    assert "예금자보호법 시행령 제18조" in generator.messages[0][1]["content"]


def test_stream_answer_question_uses_fixed_message_when_evidence_is_insufficient() -> None:
    """답변 불가 구조화 결과에서 고정 안내 한 조각 전달"""
    generator = FakeGenerator(
        rag_module.RagAnswer(
            can_answer=False,
            source_ids=[],
            answer="",
        )
    )

    chunks = list(
        rag_module.stream_answer_question(
            generator,
            "주거 금융상품을 추천해 주세요.",
            [],
        )
    )

    assert chunks == [rag_module.INSUFFICIENT_EVIDENCE_MESSAGE]


def test_stream_answer_question_does_not_expose_unknown_source_answer() -> None:
    """검색되지 않은 출처의 답변 조각 노출 방지"""
    generator = FakeGenerator(
        rag_module.RagAnswer(
            can_answer=True,
            source_ids=["S2"],
            answer="확인되지 않은 답변입니다.",
        )
    )
    articles = [
        {
            "law_name": "예금자보호법",
            "article_no": "제1조",
            "effective_date": "20260102",
            "text": "예금자 보호 목적",
        }
    ]

    chunks = list(
        rag_module.stream_answer_question(
            generator,
            "예금은 보호되나요?",
            articles,
        )
    )

    assert chunks == [rag_module.INSUFFICIENT_EVIDENCE_MESSAGE]
