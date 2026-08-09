---
date: 2026-08-09
status: completed
result: LangFeather 연결 책임을 observability 모듈로 격리하고 기존 추적 동작 유지
---

# LangFeather 연결 경계 분리

## 문제

`main.py`가 LangFeather 활성화 판단, SDK import, endpoint 설정, Graph 래핑과 종료까지
직접 처리하고 있었다. API 자원 준비 코드를 옮길 때 선택적 추적 기능까지 함께 따라가야
하는 구조였다.

## 판단

LangFeather를 완전히 삭제하면 의존성·문서·테스트를 다시 연결할 때 또 수정해야 한다.
대신 추적 도구에만 필요한 코드를 `observability` 경계로 옮겨 핵심 API와 분리했다.

## 적용

- `observability/langfeather.py`에 SDK 준비·Runnable 래핑·종료 처리 이동
- 추적이 꺼진 경우 원본 Runnable을 그대로 반환
- LangFeather 단위 테스트를 `main.py` 테스트와 분리

## 결과

RAG와 Agent Graph의 선택적 LangFeather 추적은 유지하면서 `main.py`가 SDK 설치 방식과
환경 변수 해석을 직접 알지 않게 되었다.

검증: `tests/test_langfeather_observability.py`, `tests/test_main.py`
