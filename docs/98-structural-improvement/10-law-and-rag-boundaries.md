---
date: 2026-08-09
status: completed
result: 법령 인덱싱과 RAG 실행 코드를 분리해 데이터 준비와 상담 흐름의 경계 명확화
---

# 법령과 RAG 영역 분리

## 문제

XML 파싱, 청킹, 임베딩, Chroma 접근과 검색·프롬프트·LangGraph가 모두 `chatbot` 루트에
있었다. 인덱싱 데이터를 준비하는 코드와 사용자 질문을 처리하는 코드의 차이가 파일 구조에서
드러나지 않았다.

## 판단

법령 원문을 검색 가능한 데이터로 만드는 과정은 `law/`, 준비된 인덱스에서 근거를 검색하고
답변을 만드는 과정은 `rag/`로 구분했다. 알고리즘과 설정값은 바꾸지 않고 import 경계만
정리했다.

## 적용

- `law/`: XML 파싱, 조문 청킹, KURE 임베딩, Chroma 접근
- `rag/`: dense·BM25 결합 검색, 구조화 답변 생성, Retrieval → Generation Graph
- Agent Tool, API 자원, 인덱싱·평가 스크립트의 import 변경
- 파일 이동으로 달라질 수 있던 기본 Chroma 경로를 저장소 `data/index/chroma`로 유지

## 결과

법령 데이터 준비와 온라인 상담 흐름을 폴더만 보고도 구분할 수 있다. 기존 `top_k=5`,
하이브리드 검색, RAG 구조화 출력과 공개 API 동작은 그대로 유지된다.

검증: 법령 파싱·청킹·임베딩·벡터스토어, 검색·RAG Graph, Agent·API 테스트
