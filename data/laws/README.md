# 법령 원문 XML (RAG corpus)

"예·적금 이용자를 위한 소비자보호 법령 Q&A"의 근거 문서 4건. 선정 배경과
결정은 `docs/adr/0004-select-consumer-protection-laws-corpus.md` 참고.

## 출처와 라이선스

- 출처: 국가법령정보 공동활용 Open API (https://open.law.go.kr)
- 재배포 근거: [저작권법 제7조](https://www.law.go.kr/법령/저작권법/제7조) —
  법률·명령 등은 저작권 보호를 받지 않는 저작물

## 수집 snapshot

수집일 2026-07-06 기준의 고정 snapshot이며, 실시간 법률 정보가 아니다.
정기 동기화는 아직 구현하지 않는다(ADR 0004).

| 파일 | 법령명 | 법령일련번호 | 시행일 |
| --- | --- | --- | --- |
| financial-consumer-protection-act.xml | 금융소비자 보호에 관한 법률 | 277247 | 2026-01-02 |
| financial-consumer-protection-act-decree.xml | 금융소비자 보호에 관한 법률 시행령 | 285715 | 2026-04-28 |
| depositor-protection-act.xml | 예금자보호법 | 277269 | 2026-01-02 |
| depositor-protection-act-decree.xml | 예금자보호법 시행령 | 273001 | 2025-09-01 |

## 재수집 방법

```bash
LAW_API_OC=<open.law.go.kr 이메일 ID> uv run python scripts/collect_laws.py
```

호출 전 open.law.go.kr에서 OPEN API 활용 신청(현행법령 목록·본문 XML,
호출 IP 등록)이 필요하다.
