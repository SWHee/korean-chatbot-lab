---
date: 2026-08-09
status: completed
result: main.py에서 API 계약과 Agent 실행 결과 변환을 분리해 endpoint의 흐름만 남김
---

# API 계약과 응답 변환 분리

## 문제

`main.py`가 서버 시작·공유 자원 준비·endpoint뿐 아니라 요청/응답 모델과 LangGraph
결과를 API 형식으로 바꾸는 코드까지 함께 가지고 있었다. API를 확인할 때 실제 요청 흐름과
응답 조립 코드가 섞여 보였다.

## 판단

이번에는 endpoint의 동작을 바꾸지 않고, 두 책임만 분리했다.

- `api/models.py`: FastAPI가 받거나 반환하는 데이터 형식
- `api/responses.py`: 누적된 Agent 메시지에서 Tool 실행·법령 근거·예적금 후보를 추출하는 변환

`main.py`는 아직 서버 수명주기와 RAG·Agent Graph 준비를 맡는다. 이를 추가로 옮기면
실제 자원 초기화 방식까지 함께 바뀌므로 다음 작은 작업으로 남겼다.

## 적용

- 기존 요청·응답 Pydantic 모델 7개를 `chatbot.api.models`로 이동
- Agent 응답 조립과 SSE 형식 변환을 `chatbot.api.responses`로 이동
- 적금 결과의 `product_type`, `reserve_type_name`이 분리 뒤에도 유지되는 테스트 추가

## 결과

`main.py`의 endpoint는 입력 검증, Graph 호출, 응답 반환 흐름을 읽는 파일이 되었다.
분리된 모듈이 적금 Tool 결과를 기존과 같은 API 응답으로 변환함을 테스트로 확인했다.

검증: `tests/test_main.py`
