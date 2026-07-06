from pathlib import Path

from chatbot.statutes import parse_law

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "laws"

# 전문(장·절 표제) 제외한 조문 수
EXPECTED_COUNTS = {
    "financial-consumer-protection-act.xml": 73,
    "financial-consumer-protection-act-decree.xml": 53,
    "depositor-protection-act.xml": 86,
    "depositor-protection-act-decree.xml": 48,
}


def test_parse_all_laws_article_counts() -> None:
    """4개 법령 파싱 결과가 전문 제외 조문 수와 일치"""
    for filename, count in EXPECTED_COUNTS.items():
        articles = parse_law(DATA_DIR / filename)
        assert len(articles) == count, filename


def test_article_metadata_and_text() -> None:
    """예보법 시행령 제18조의 메타데이터와 본문 내용"""
    articles = parse_law(DATA_DIR / "depositor-protection-act-decree.xml")
    article = next(a for a in articles if a.article_no == "제18조")
    assert article.law_name == "예금자보호법 시행령"
    assert article.title == "보험금의 계산방법의 예외 등"
    assert article.effective_date == "20250901"
    assert "1억원" in article.text


def test_branch_article_number() -> None:
    """제N조의M 가지번호 표기"""
    articles = parse_law(DATA_DIR / "depositor-protection-act-decree.xml")
    numbers = {a.article_no for a in articles}
    assert "제3조의2" in numbers
    assert len(numbers) == len(articles)  # 조문 번호 중복 없음
