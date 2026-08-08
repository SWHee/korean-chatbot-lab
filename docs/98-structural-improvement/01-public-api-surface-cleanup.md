---
date: 2026-08-08
status: completed
result: 현재 서비스와 법령 진단에 필요한 API만 공개하고 과거 Workflow는 내부 코드로 보존
---

# 공개 API 경로 정리

## 문제

`main.py`가 현재 Agent API뿐 아니라 과거 학습 단계의 RAG 스트리밍과 Routed
Workflow API까지 함께 노출하고 있었다. 프론트는 `/ask-agent/stream`만 사용하는데 Swagger에는
서로 다른 시기의 실행 경로가 나란히 보여 현재 서비스 경계를 파악하기 어려웠다.

## 판단

- `/ask-rag`: Agent와 분리해 법령 검색·생성을 진단하는 경로로 유지
- `/ask-agent`, `/ask-agent/stream`: 현재 서비스 경로로 유지
- `/ask-rag/stream`: 현재 프론트에서 사용하지 않아 공개 API에서 제거
- `/ask-workflow`: Agent 이전의 고정 라우팅 학습 결과이므로 공개 API에서 제거

`create_rag_graph()`와 `create_routed_workflow_graph()`는 삭제하지 않았다. 전자는 기존
24문항 법령 회귀 평가를 이용할 경우(Agentic RAG로 넘어오면서, 현재는 기존 선형 구조 평가 베이스라인 지표와 비교해도 되는 것일까? 라는 의문점에서 시작해서 나중에 개선 지표를 쓸 때 애매하다고 생각했다)에 사용하고, 후자는 LangGraph의 고정 분기·혼합 경로를 검증한
내부 코드와 테스트로 보존.

## 적용

- Workflow 전용 요청·응답 모델과 자원 초기화 제거
- 사용하지 않는 RAG 일반 텍스트 스트리밍 endpoint 제거
- OpenAPI에 공개할 경로를 테스트로 고정
- 예금·적금 통합 반환값과 달랐던 Agent 상품 타입 표기 수정

## 결과

Swagger에는 `/ask-rag`, `/ask-agent`, `/ask-agent/stream`만 상담 관련 경로로 남아있다.
내부 RAG 평가와 Routed Workflow 테스트는 기존 그래프를 직접 사용하므로 영향을 받지
않음을 확인했다.

검증: `149 passed, 2 skipped`
