---
date: 2026-08-09
status: completed
result: 상담 endpoint를 APIRouter로 분리하고 main.py를 application 진입점으로 축소
---

# API endpoint 분리

## 문제

요청·응답 모델과 자원 준비를 분리한 뒤에도 `main.py`가 RAG 호출, Agent 실행과 SSE
이벤트 흐름을 모두 포함하고 있었다.

## 판단

외부에 공개하는 URL과 요청 처리 흐름은 하나의 router로 묶고, `main.py`는 FastAPI 앱을
만들어 router와 수명주기를 연결하는 역할만 맡겼다.

## 적용

- `/ask-rag`, `/ask-agent`, `/ask-agent/stream`을 `api/routes.py`로 이동
- 기존 URL·응답 모델·SSE event 이름 유지
- Router 자체의 공개 경로 테스트 추가

## 결과

`main.py`는 FastAPI 생성과 router 등록만 남은 application 진입점이 되었다. endpoint
구현은 API 폴더에서 요청 모델·응답 변환·자원 준비 코드와 함께 확인할 수 있다.

검증: `tests/test_api_routes.py`, `tests/test_main.py`
