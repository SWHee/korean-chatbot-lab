---
date: 2026-08-09
status: completed
result: RAG·Agent Graph 생성과 공유 자원 준비를 main.py 밖으로 분리
---

# API 자원 준비 분리

## 문제

`main.py`가 endpoint 실행뿐 아니라 임베딩 모델, Chroma collection, RAG Graph,
Agent Tool과 SQLite Checkpointer를 만드는 순서까지 직접 알고 있었다.

## 판단

이 자원들은 여러 endpoint가 공유하고 서버 요청 중 한 번만 준비된다. FastAPI의
`app.state` 사용은 유지하되 생성 책임만 `api/resources.py`로 옮겼다.

## 적용

- `prepare_rag_resources()`와 `prepare_agent_resources()` 이동
- RAG·Agent의 LangFeather trace 이름도 자원 모듈로 이동
- 자원 생성 테스트를 `tests/test_api_resources.py`로 분리

## 결과

`main.py`는 자원을 준비해 달라고 요청할 뿐, Graph와 Tool의 조립 방법을 직접 알지
않게 되었다. 기존 지연 초기화와 자원 공유 방식은 유지했다.

검증: `tests/test_api_resources.py`, `tests/test_main.py`
