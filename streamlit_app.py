"""법령 RAG 스트리밍 API를 대화형으로 확인하는 Streamlit UI"""

import os
from collections.abc import Iterator
from datetime import datetime
from itertools import chain

import httpx
import streamlit as st


DEFAULT_API_URL = os.getenv("CHATBOT_API_URL", "http://127.0.0.1:8000")
RAG_STREAM_PATH = "/ask-rag/stream"
WELCOME_MESSAGE = (
    "안녕하세요. 예금자보호와 금융소비자 권리에 관한 법령을 찾아 "
    "쉽게 설명해 드릴게요."
)
SUGGESTED_QUESTIONS = (
    "은행이 파산하면 내 예금은 얼마까지 보호받나요?",
    "예금자보호제도는 무엇인가요?",
    "금융상품 설명을 제대로 듣지 못했다면 어떻게 해야 하나요?",
)
SEARCHING_NOTICE = "법령에서 근거 조문을 찾고 있어요..."
CONNECTION_ERROR_MESSAGE = (
    "답변 서버에 연결하지 못했습니다. FastAPI와 Ollama가 실행 중인지 "
    "확인해 주세요."
)


def stream_rag_answer(api_url: str, question: str) -> Iterator[str]:
    """FastAPI 법령 RAG 응답을 텍스트 조각으로 전달"""
    endpoint = f"{api_url.rstrip('/')}{RAG_STREAM_PATH}"
    with httpx.stream(
        "POST",
        endpoint,
        json={"question": question},
        timeout=180.0,
    ) as response:
        response.raise_for_status()
        yield from response.iter_text()


def render_sidebar() -> str:
    """API 연결 설정과 대화 초기화 기능 표시"""
    with st.sidebar:
        st.markdown("### ⚙️ 연결 설정")
        api_url = st.text_input(
            "FastAPI 주소",
            value=DEFAULT_API_URL,
            help="먼저 FastAPI 서버를 실행해 주세요.",
        )

        st.markdown("---")
        st.markdown("#### 현재 답변 범위")
        st.caption("금융소비자보호법 · 예금자보호법과 각 시행령을 검색합니다.")
        st.caption("화면은 대화를 보관하지만, 모델은 아직 이전 질문을 기억하지 않습니다.")

        st.markdown("---")
        if st.button("🗑️ 대화 내용 지우기", width="stretch"):
            st.session_state.messages = [
                {"role": "assistant", "content": WELCOME_MESSAGE}
            ]
            st.rerun()

    return api_url


def render_header() -> None:
    """서비스 소개와 주의 문구 표시"""
    st.markdown(
        """
        <section class="chat-header">
            <div class="profile-badge">₩</div>
            <div class="header-titles">
                <h1>금융안심 챗봇</h1>
                <p>예금자보호 · 금융소비자 법령을 근거와 함께 안내해 드려요</p>
            </div>
            <div class="header-status"><span class="status-dot"></span>상담 가능</div>
        </section>
        <p class="chat-disclaimer">
            학습·시연용 서비스입니다 · 최신 법령과 개별 금융상품의 보호 여부는
            공식 공시에서 다시 확인해 주세요
        </p>
        """,
        unsafe_allow_html=True,
    )


def render_date_divider() -> None:
    """메신저 스타일의 대화 날짜 구분선"""
    today = datetime.now().strftime("%Y년 %m월 %d일")
    st.markdown(
        f'<div class="date-divider"><span>{today}</span></div>',
        unsafe_allow_html=True,
    )


def render_suggested_questions() -> str | None:
    """첫 화면에서 바로 눌러볼 수 있는 추천 질문 목록"""
    selected_question = None
    with st.container(key="suggested-questions"):
        st.markdown(
            '<p class="suggest-label">💡 이런 질문을 해보세요</p>',
            unsafe_allow_html=True,
        )
        for question in SUGGESTED_QUESTIONS:
            if st.button(question, width="stretch"):
                selected_question = question
    return selected_question


def render_styles() -> None:
    """메신저형 대화 화면의 색상과 말풍선 조정"""
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at 12% -10%, #cfdfec 0%, transparent 42%),
                linear-gradient(180deg, #a9c1d5 0%, #b2c7d9 55%, #a6bed2 100%);
        }
        [data-testid="stHeader"] { background: transparent; }
        .stMainBlockContainer {
            max-width: 780px;
            padding-top: 1.2rem;
            padding-bottom: 7.5rem;
        }

        /* 상단 프로필 카드 */
        .chat-header {
            display: flex;
            align-items: center;
            gap: .85rem;
            padding: .95rem 1.15rem;
            margin-bottom: .5rem;
            background: rgba(255, 255, 255, .92);
            backdrop-filter: blur(6px);
            border: 1px solid rgba(255, 255, 255, .65);
            border-radius: 18px;
            box-shadow: 0 8px 24px rgba(43, 63, 80, .14);
        }
        .profile-badge {
            display: grid;
            flex: 0 0 46px;
            height: 46px;
            place-items: center;
            color: #3b1e1e;
            background: linear-gradient(135deg, #ffe14d, #fdd800);
            border-radius: 16px;
            font-size: 1.35rem;
            font-weight: 800;
            box-shadow: inset 0 -2px 4px rgba(0, 0, 0, .08);
        }
        .header-titles h1 {
            margin: 0;
            color: #232323;
            font-size: 1.25rem;
            letter-spacing: -.01em;
        }
        .header-titles p {
            margin: .15rem 0 0;
            color: #6c757d;
            font-size: .84rem;
        }
        .header-status {
            margin-left: auto;
            color: #4c6274;
            font-size: .78rem;
            font-weight: 600;
            white-space: nowrap;
        }
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            margin-right: .35rem;
            background: #2ecc71;
            border-radius: 50%;
            box-shadow: 0 0 0 3px rgba(46, 204, 113, .22);
        }
        .chat-disclaimer {
            margin: 0 0 .9rem;
            padding: .5rem .9rem;
            color: #55677a;
            background: rgba(255, 255, 255, .5);
            border-radius: 10px;
            font-size: .76rem;
            text-align: center;
        }

        /* 대화 날짜 구분선 */
        .date-divider { margin: .4rem 0 .8rem; text-align: center; }
        .date-divider span {
            padding: .3rem .9rem;
            color: #f2f7fb;
            background: rgba(72, 94, 111, .45);
            border-radius: 999px;
            font-size: .74rem;
        }

        /* 말풍선 */
        [data-testid="stChatMessage"] {
            align-items: flex-start;
            gap: .55rem;
            padding: .35rem 0;
            background: transparent;
            animation: bubble-in .18s ease-out;
        }
        @keyframes bubble-in {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: none; }
        }
        [data-testid="stChatMessageContent"] {
            flex: 0 1 auto;
            max-width: min(78%, 600px);
            padding: .72rem .95rem;
            color: #222;
            background: white;
            border-radius: 4px 16px 16px 16px;
            box-shadow: 0 1px 2px rgba(30, 47, 61, .14);
            font-size: .95rem;
            line-height: 1.6;
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            justify-content: flex-end;
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
        [data-testid="stChatMessageContent"] {
            width: fit-content;
            background: #fee500;
            border-radius: 16px 4px 16px 16px;
            box-shadow: 0 1px 2px rgba(94, 78, 0, .18);
        }
        [data-testid="stChatMessageAvatarUser"] { display: none; }
        [data-testid="stChatMessageAvatarAssistant"] {
            color: #3b1e1e;
            background: linear-gradient(135deg, #ffe14d, #fdd800);
            border-radius: 14px;
        }

        /* 추천 질문 */
        .st-key-suggested-questions { margin-top: .3rem; }
        .suggest-label {
            margin: 0 0 .1rem .15rem;
            color: #40586d;
            font-size: .8rem;
            font-weight: 700;
        }
        .st-key-suggested-questions .stButton > button {
            justify-content: flex-start;
            padding: .55rem .95rem;
            color: #33475b;
            background: rgba(255, 255, 255, .85);
            border: 1px solid rgba(255, 255, 255, .9);
            border-radius: 14px;
            box-shadow: 0 1px 3px rgba(43, 63, 80, .10);
            font-size: .87rem;
            text-align: left;
            transition: all .15s ease;
        }
        .st-key-suggested-questions .stButton > button:hover {
            background: white;
            border-color: #ffd400;
            box-shadow: 0 4px 10px rgba(43, 63, 80, .16);
            transform: translateY(-1px);
        }

        /* 입력창 */
        [data-testid="stBottom"] > div { background: transparent; }
        div[data-testid="stChatInput"] {
            background: white;
            border: 1px solid rgba(0, 0, 0, .06);
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(38, 57, 72, .22);
        }

        /* 사이드바 */
        [data-testid="stSidebar"] {
            background: #f7f8fa;
            border-right: 1px solid rgba(0, 0, 0, .08);
        }
        [data-testid="stSidebar"] .stButton > button {
            background: #fff6a5;
            border-color: #e5cf00;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """채팅 기록을 표시하고 새 질문의 스트리밍 답변 수신"""
    st.set_page_config(
        page_title="금융안심 챗봇",
        page_icon="💬",
        layout="centered",
    )
    render_styles()
    api_url = render_sidebar()
    render_header()

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]

    render_date_divider()
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    selected_question = None
    if len(st.session_state.messages) <= 1:
        selected_question = render_suggested_questions()

    question = st.chat_input("금융소비자 보호 제도에 관해 물어보세요")
    question = question or selected_question
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            answer_stream = stream_rag_answer(api_url, question)
            # 검색·모델 준비 동안 빈 말풍선 대신 진행 상태 표시
            with st.spinner(SEARCHING_NOTICE):
                first_piece = next(answer_stream, "")
            answer = st.write_stream(chain([first_piece], answer_stream))
        except httpx.HTTPError as error:
            answer = CONNECTION_ERROR_MESSAGE
            st.error(answer)
            st.caption(str(error))

    st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
