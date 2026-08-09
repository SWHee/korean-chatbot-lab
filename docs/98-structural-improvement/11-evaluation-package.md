---
date: 2026-08-09
status: completed
result: RAG·Agent 평가 계약과 LangSmith 실행을 한 패키지로 모으고 scripts를 실행 진입점으로 축소
---

# 평가 영역 분리

## 문제

RAG Dataset 실행, 검색·충실도 평가자와 Agent 개발 Dataset 계약이 `chatbot` 루트와
`agent/`에 나뉘어 있었다. LangSmith 실행 스크립트도 평가 로직 전체를 포함해 서비스 코드와
평가 코드의 위치를 한눈에 파악하기 어려웠다.

## 판단

평가 대상이 RAG인지 Agent인지와 관계없이 평가 전용 코드는 `evaluation/`에 모았다.
`scripts/`는 기존 명령을 유지하기 위한 실행 진입점으로만 남겼다.

## 적용

- `evaluation/rag_dataset.py`: 24문항 RAG 실행 계약
- `evaluation/agent_dataset.py`: 32개 Agent 개발 사례 계약
- `evaluation/metrics.py`: 검색 Precision·Recall과 충실도 평가자
- `evaluation/runner.py`, `registry.py`: LangSmith 평가 실행과 Dataset 등록
- 기존 두 실행 스크립트를 `main()` 호출만 남은 진입점으로 축소

## 결과

평가 코드가 실제 상담 Agent와 분리되었고 기존 `scripts/run_rag_evaluation.py --all`과
Dataset 등록 명령은 그대로 사용할 수 있다. Dataset 이름, 문항, 모델과 지표 설정은 바뀌지 않았다.

검증: RAG·Agent Dataset, 평가자, LangSmith 실행·등록 테스트와 평가 CLI 도움말
