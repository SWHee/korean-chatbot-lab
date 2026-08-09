---
date: 2026-08-09
status: completed
result: 현재 실행되지 않는 고정 Routed Workflow POC를 제거하고 법령 RAG Graph만 보존
---

# 고정 Routed Workflow 제거

## 문제

`graph.py`에는 현재 사용하는 법령 RAG뿐 아니라 Agent 전환 전에 만든 상품 조회, 고정
분기, 질문 분석과 mixed 병렬 Workflow가 함께 남아 있었다. 공개 endpoint는 이미
제거됐지만 전용 구현과 테스트 때문에 현재 흐름처럼 보일 수 있었다.

## 확인

런타임과 평가 스크립트가 사용하는 항목은 `create_rag_graph()`뿐이었다. 현재 Agent는
`agent/graph.py`에서 Tool calling, `clarify`, 범위 밖 응답과 SQLite 멀티턴을 처리한다.

## 적용

- 고정 상품·분기·질문 분석·mixed·Routed Workflow Graph 제거
- Routed Workflow 전용 테스트 제거
- Agent가 사용하던 `ProductFilters`와 범위 안내 문구를 Agent 영역으로 이동
- 과거 명세와 트러블슈팅 문서에 역사적 구현임을 표시

## 결과

`graph.py`에는 `/ask-rag`와 24문항 법령 회귀 평가가 사용하는 Retrieval → Generation
Graph만 남았다. 현재 서비스 Agent와 과거 Workflow의 코드 경계가 분명해졌다.

검증: `tests/test_graph.py`, Agent Graph 관련 테스트, 전체 Python 테스트
