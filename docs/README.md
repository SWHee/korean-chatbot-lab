# 개발 문서

이 문서는 핀봄의 개발 상태와 상세 기록을 찾는 허브입니다. 루트
[README](../README.md)는 현재 실행 가능한 기능, 데이터 범위와 실행 방법만 다룹니다.
구현 예정 작업, 공개 README 핫픽스와 개발 과정의 판단은 이곳에서 관리합니다.

## 진행 중 및 예정 작업

| 주제 | 현재 문서 |
| --- | --- |
| 법령 검색 견고성·Hybrid Search·Reranker 비교 | [법령 검색 견고성 개선 지도](00-performance-improvement/04-retrieval-robustness/README.md) |
| Finlife 예·적금과 Agent 기능 확장 | [Finlife Agent 실행 명세](07-langgraph-agent/01-finlife-agent-expansion-spec.md) |
| Agent 평가 데이터와 검증 경계 | [Agent 개발 데이터셋 계약](07-langgraph-agent/05-agent-evaluation-dataset-contract.md) |
| 공개 README·대표 이미지·발표 자료 정리 | [공개 README 기준선](10-project-presentation/01-readme-baseline.md) |

이 표는 완료된 기능 목록이 아닙니다. 각 문서의 상태와 검증 결과를 기준으로 실제
진행 여부를 판단하며, 구현이 끝난 내용만 루트 README에 반영합니다.

## 현재 구현과 검증

| 주제 | 확인할 문서 |
| --- | --- |
| 법령 RAG의 수집·청킹·검색 흐름 | [RAG 파이프라인 개요](02-langchain-rag/03-guides/01-rag-pipeline-overview.md) |
| RAG 개발·회귀평가 데이터셋 | [평가 데이터 안내](../data/evaluation/README.md) |
| LangGraph 전환 전후의 RAG 회귀 기준선 | [전환 결과](03-langsmith-evaluation/11-langgraph-migration-results.md) |
| Agent 도구·멀티턴 데이터셋 계약 | [Agent 개발 데이터셋 계약](07-langgraph-agent/05-agent-evaluation-dataset-contract.md) |
| 법령 원문의 출처와 재수집 방법 | [법령 데이터 안내](../data/laws/README.md) |

RAG 24문항 결과는 개발·회귀 기준선이며 Agent 전체 품질을 대표하는 최종 성능 점수가
아닙니다. Agent 평가 데이터셋은 도구 호출과 멀티턴 동작을 검증하기 위한 계약·fixture
단계입니다.

## 설계와 구현 기록

| 주제 | 문서 |
| --- | --- |
| 법령 코퍼스·임베딩·벡터 저장소 선택 | [RAG ADR](02-langchain-rag/01-adr/) |
| 성능·응답 신뢰성 개선 | [성능 개선 기록](00-performance-improvement/README.md) |
| LangGraph 마이그레이션 | [LangGraph 전환 기록](04-langgraph-migration/) |
| Agent 확장 설계와 도구 경계 | [LangGraph Agent 문서](07-langgraph-agent/) |
| Agent 오류와 스트리밍 문제 해결 | [Agent troubleshooting](07-langgraph-agent/troubleshooting/) |
| CI/CD와 실행 환경 | [CI/CD 문서](08-ci-cd-pipeline/README.md) |
| 기존 Next.js UI 기준선 | [기존 UI 문서](09-frontend/02-nextjs-chat-ui.md) |
| 현재 프론트엔드의 배경·상담 화면 기록 | [frontend 문서](../frontend/docs/) |

## 회고와 개인 기록

[주차별 회고](99-retrospectives/)는 학습 과정과 당시 판단을 남긴 개인 기록입니다.
현재 제품 요구사항, 설계 결정이나 성능 근거로 사용하지 않으며 개발 흐름을 시간순으로
되짚을 때만 참고합니다.

## 권장 읽기 순서

처음 코드를 읽는 경우에는 **법령 데이터 안내 → RAG 파이프라인 → Finlife Agent 실행
명세 → Agent 개발 데이터셋 계약 → 현재 UI 문서** 순서를 권장합니다. 특정 개선의
배경이나 과거 비교 결과가 필요할 때만 성능 개선, LangSmith와 회고 문서를 참고합니다.

## 문서 관리 기준

- 루트 README에는 현재 코드와 직접 확인한 실행 방법만 둡니다.
- 구현 예정, 실험 후보와 README 핫픽스는 이 허브에서 관련 문서에 연결합니다.
- 실험 수치에는 데이터셋·법령 코퍼스·모델·주요 설정을 함께 기록합니다.
- 완료되지 않은 항목을 구현된 기능처럼 표현하지 않습니다.
- 회고는 기술 문서의 근거로 인용하지 않고 개인 학습 기록으로 구분합니다.
