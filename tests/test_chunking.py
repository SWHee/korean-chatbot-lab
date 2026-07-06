from pathlib import Path

from chatbot.chunking import chunk_articles
from chatbot.statutes import parse_law

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "laws"


def load_articles():
    """4개 법령 전체 조문 로드"""
    articles = []
    for f in sorted(DATA_DIR.glob("*.xml")):
        articles += parse_law(f)
    return articles


def test_deleted_stubs_excluded() -> None:
    """예보법 삭제 스텁 2건 제외, 부분 삭제 조문은 유지"""
    chunks = chunk_articles(load_articles())
    act = {c.article_no for c in chunks if c.law_name == "예금자보호법"}
    assert "제19조" not in act
    assert "제38조의2" not in act
    decree = {c.article_no for c in chunks if c.law_name == "예금자보호법 시행령"}
    assert "제15조" in decree  # 항 4개가 삭제된 부분 삭제 조문은 유지


def test_chunk_size_and_boundary() -> None:
    """본문이 max_chars 이하이고 모든 청크가 단일 조문 소속"""
    chunks = chunk_articles(load_articles(), max_chars=1000, overlap=100)
    for c in chunks:
        header, body = c.text.split("\n", 1)
        assert header.startswith(f"[{c.law_name} {c.article_no}")
        assert len(body) <= 1000


def test_split_children_keep_metadata() -> None:
    """분할된 자식 청크의 메타데이터 복사와 순번"""
    articles = parse_law(DATA_DIR / "depositor-protection-act-decree.xml")
    chunks = chunk_articles(articles, max_chars=1000, overlap=100)
    children = [c for c in chunks if c.article_no == "제18조"]
    assert len(children) >= 2  # 제18조는 1,000자 초과라 분할됨
    assert [c.chunk_index for c in children] == list(range(len(children)))
    assert all(c.effective_date == "20250901" for c in children)
    assert any("1억원" in c.text for c in children)
