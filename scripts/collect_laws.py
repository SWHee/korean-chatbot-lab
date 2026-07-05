"""법령 원문 XML 1회 수집 (ADR 0004). 사용법은 data/laws/README.md 참고."""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"

# 법령명 → 저장 파일명 (ADR 0004의 corpus 4건)
LAWS = {
    "금융소비자 보호에 관한 법률": "financial-consumer-protection-act.xml",
    "금융소비자 보호에 관한 법률 시행령": "financial-consumer-protection-act-decree.xml",
    "예금자보호법": "depositor-protection-act.xml",
    "예금자보호법 시행령": "depositor-protection-act-decree.xml",
}

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "laws"


def find_current_law(client: httpx.Client, oc: str, name: str) -> dict:
    """법령명 정확 일치 + 현행 법령의 검색 메타데이터 조회"""
    params = {"OC": oc, "target": "law", "type": "XML", "query": name, "display": 50}
    resp = client.get(SEARCH_URL, params=params)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    if root.tag == "Response":  # 미등록 OC 등 오류는 <Response> 루트로 반환됨
        sys.exit(f"API 오류: {root.findtext('msg')}")
    for law in root.iter("law"):
        if law.findtext("법령명한글") == name and law.findtext("현행연혁코드") == "현행":
            return {
                "일련번호": law.findtext("법령일련번호"),
                "시행일자": law.findtext("시행일자"),
                "공포일자": law.findtext("공포일자"),
            }
    sys.exit(f"현행 법령을 찾지 못함: {name}")


def fetch_law_body(client: httpx.Client, oc: str, mst: str) -> bytes:
    """법령일련번호(MST)로 본문 XML 원문 조회, root <법령> 검증"""
    params = {"OC": oc, "target": "law", "type": "XML", "MST": mst}
    resp = client.get(SERVICE_URL, params=params)
    resp.raise_for_status()
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        sys.exit(f"본문이 XML이 아님: MST={mst}")
    if root.tag != "법령":
        sys.exit(f"본문 조회 오류: MST={mst}, root=<{root.tag}>")
    return resp.content


def main() -> None:
    oc = os.environ.get("LAW_API_OC")
    if not oc:
        sys.exit("환경 변수 LAW_API_OC 필요 (open.law.go.kr 이메일 ID)")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30) as client:
        for name, filename in LAWS.items():
            meta = find_current_law(client, oc, name)
            body = fetch_law_body(client, oc, meta["일련번호"])
            path = OUT_DIR / filename
            path.write_bytes(body)
            print(
                f"{name}: 일련번호 {meta['일련번호']}, "
                f"시행 {meta['시행일자']}, {len(body):,}바이트 → {path.name}"
            )


if __name__ == "__main__":
    main()
