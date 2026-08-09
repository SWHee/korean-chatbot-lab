---
date: 2026-08-09
status: completed
result: 서비스 기능을 유지한 채 src/chatbot을 책임별 8개 영역으로 정리하고 전체 회귀 검증 완료
---

# src 구조 개선 결과

## 최종 구조

```text
chatbot/
├── agent/          # Tool calling·clarify·SQLite 멀티턴
├── api/            # FastAPI 계약·route·수명주기·공유 자원
├── evaluation/     # RAG·Agent Dataset과 LangSmith 평가
├── generation/     # Anthropic·Ollama 생성기와 선택 factory
├── law/            # 법령 파싱·청킹·임베딩·Chroma
├── observability/  # 선택적 LangFeather 연결
├── products/       # Finlife 예·적금 조회·정규화·비교
├── rag/            # 하이브리드 검색·구조화 답변·RAG Graph
├── main.py         # FastAPI application 진입점
└── settings.py     # 로컬 환경 변수 로드
```

## 유지한 기능

- `/ask-rag`, `/ask-agent`, `/ask-agent/stream` API 계약
- 법령 dense·BM25 하이브리드 검색과 구조화 답변
- 예금·적금 Tool calling과 clarify 멀티턴
- SQLite checkpoint, Anthropic 기본 생성과 Ollama 수동 선택
- 24문항 RAG 평가와 32개 Agent 개발 Dataset 계약
- 기존 인덱싱·평가 script 실행 경로

## 검증 결과

- Python: `132 passed, 2 skipped`
- Frontend: `16 passed`
- Next.js production build 성공
- Docker Compose 구성 검증 성공
- 제거된 과거 모듈 import 잔존 없음

이번 작업은 기능 추가가 아니라 책임의 위치를 정리한 리팩터링이다. 검색 성능이나 답변 품질을
바꾸는 작업은 이 구조를 기준으로 별도 비교와 평가를 거쳐 진행한다.
