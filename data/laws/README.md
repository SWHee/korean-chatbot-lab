# 법령 원문 XML (RAG corpus)

"예·적금 이용자를 위한 소비자보호 법령 Q&A"의 근거 문서 4건. 선정 배경과
결정은 `docs/02-langchain-rag/01-adr/0004-select-consumer-protection-laws-corpus.md` 참고.

## 출처와 라이선스

- 출처: 국가법령정보 공동활용 Open API (https://open.law.go.kr)
- 재배포 근거: [저작권법 제7조](https://www.law.go.kr/법령/저작권법/제7조) —
  법률·명령 등은 저작권 보호를 받지 않는 저작물
- 활용 기준: 원문과 파생 데이터에는 출처, 수집일, snapshot 기준을 함께 남긴다.
  API 인증 정보와 호출 IP 같은 신청 정보는 커밋하지 않는다.

이 저장소의 XML은 위 출처에서 받은 법령 원문 snapshot이다. 조문 단위 파싱본,
청크 목록처럼 사람이 확인 가능한 파생 데이터도 같은 출처와 생성 방법을
명시하면 저장소에 남길 수 있다. 다만 Chroma 인덱스, 모델 weight, cache처럼
코드로 재생성 가능한 바이너리성 산출물은 커밋하지 않는다.

주의: 이 데이터는 학습용 RAG corpus이며 공식 법령정보 서비스나 법률 자문을
대체하지 않는다. 실제 서비스나 배포 전에는 국가법령정보 공동활용 조건과
최신 법령 여부를 다시 확인한다.

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
