---
date: 2026-08-09
status: completed
result: FastAPI 시작·종료와 공유 자원 해제를 lifecycle 모듈로 분리
---

# API 수명주기 분리

## 문제

`main.py`가 endpoint와 함께 생성기 초기화, LangFeather 종료 대기, SQLite 연결 종료와
`app.state` 정리를 처리하고 있었다.

## 판단

서버 시작·종료는 요청 처리와 다른 책임이다. 기존 `asynccontextmanager` 흐름과 정리
순서는 그대로 두고 `api/lifecycle.py`로 이동했다.

## 적용

- 생성 backend 준비와 공유 상태 정리 이동
- 정리할 `app.state` 이름을 하나의 상수로 관리
- 수명주기 테스트를 `tests/test_api_lifecycle.py`로 분리

## 결과

`main.py`에서 서버 종료 세부 구현이 사라졌고, FastAPI 앱은 분리된 `lifespan`을 받아
사용한다. 생성기 준비 순서와 LangFeather·SQLite 종료 동작은 유지했다.

검증: `tests/test_api_lifecycle.py`, `tests/test_main.py`
