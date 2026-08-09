"""법령 XML → 조문 단위 문서 파싱"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# 조문 본문을 구성하는 태그 (문서 순서대로 수집)
CONTENT_TAGS = ("조문내용", "항내용", "호내용", "목내용")


@dataclass(frozen=True)
class Article:
    """조문 하나와 근거 인용용 메타데이터"""

    law_name: str
    article_no: str
    title: str
    text: str
    effective_date: str


def parse_law(path: str | Path) -> list[Article]:
    """법령 XML에서 조문 단위 목록 추출 (장·절 표제 제외)"""
    root = ET.parse(path).getroot()
    law_name = (root.findtext("기본정보/법령명_한글") or "").strip()
    law_date = (root.findtext("기본정보/시행일자") or "").strip()

    articles = []
    for unit in root.iter("조문단위"):
        if unit.findtext("조문여부") != "조문":  # '전문'은 장·절 표제
            continue
        article_branch = unit.findtext("조문가지번호")
        article_no = f"제{unit.findtext('조문번호')}조"
        if article_branch:
            article_no += f"의{article_branch}"
        text = "\n".join(
            content.strip()
            for elem in unit.iter()
            if elem.tag in CONTENT_TAGS and (content := "".join(elem.itertext())).strip()
        )
        articles.append(
            Article(
                law_name=law_name,
                article_no=article_no,
                title=(unit.findtext("조문제목") or "").strip(),
                text=text,
                effective_date=(unit.findtext("조문시행일자") or law_date).strip(),
            )
        )
    return articles
