"""조문 → 검색용 청크 변환 (조문 경계 보존, 긴 조문만 내부 분할)"""

import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from chatbot.statutes import Article

# 조문 전체가 삭제된 스텁 ("제19조 삭제 <1997.12.31>" 한 줄)
_DELETED_STUB = re.compile(r"^제\d+조(의\d+)?\s*삭제\s*<")


@dataclass(frozen=True)
class Chunk:
    """검색·인용 단위 텍스트와 출처 메타데이터"""

    law_name: str
    article_no: str
    title: str
    text: str
    effective_date: str
    chunk_index: int


def _source_header(article: Article) -> str:
    """자식 청크가 단독으로 출처를 식별하기 위한 헤더"""
    if article.title:
        return f"[{article.law_name} {article.article_no} | {article.title}]"
    return f"[{article.law_name} {article.article_no}]"


def chunk_articles(
    articles: list[Article], max_chars: int = 1000, overlap: int = 100
) -> list[Chunk]:
    """조문 목록을 청크 목록으로 변환

    조문이 max_chars 이하면 그대로 청크 하나, 초과하면 조문 내부에서만
    재귀 분할. 모든 청크는 정확히 하나의 조문에 속한다.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars, chunk_overlap=overlap, separators=["\n", " ", ""]
    )
    chunks = []
    for article in articles:
        if _DELETED_STUB.match(article.text) and len(article.text.splitlines()) == 1:
            continue
        header = _source_header(article)
        if len(article.text) <= max_chars:
            pieces = [article.text]
        else:
            pieces = splitter.split_text(article.text)
        for i, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    law_name=article.law_name,
                    article_no=article.article_no,
                    title=article.title,
                    text=f"{header}\n{piece}",
                    effective_date=article.effective_date,
                    chunk_index=i,
                )
            )
    return chunks
