"""현재 RAG Dataset을 사용하는 인덱스 검증 스크립트 계약"""

from pathlib import Path
from runpy import run_path


SCRIPT = run_path(
    Path(__file__).resolve().parent.parent / "scripts" / "verify_index.py"
)
load_retrieval_cases = SCRIPT["load_retrieval_cases"]


def test_load_retrieval_cases_uses_current_dataset_labels() -> None:
    """검색 평가 대상 문항과 최신 필수 조문 로드"""
    cases = load_retrieval_cases()

    assert len(cases) == 15
    case_by_id = {case_id: answer_articles for case_id, _, answer_articles in cases}
    assert case_by_id["A2"] == {
        ("예금자보호법", "제2조"),
        ("예금자보호법", "제32조"),
        ("예금자보호법 시행령", "제18조"),
    }
