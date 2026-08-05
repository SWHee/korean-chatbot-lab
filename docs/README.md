# 개발 문서

이 문서는 핀봄의 구현 과정과 검증 기록을 찾는 출발점입니다. 루트
[README](../README.md)는 현재 실행 가능한 프로토타입, 데이터 범위와 실행 방법만
다룹니다.

## 현재 구현과 검증

| 주제 | 확인할 문서 |
| --- | --- |
| 법령 RAG의 수집·청킹·검색 흐름 | [RAG 파이프라인 개요](02-langchain-rag/03-guides/01-rag-pipeline-overview.md) |
| RAG 개발·회귀평가 Dataset | [평가 데이터 안내](../data/evaluation/README.md) |
| LangGraph 전환 전후의 RAG 회귀 기준선 | [전환 결과](03-langsmith-evaluation/11-langgraph-migration-results.md) |
| Agent Tool·멀티턴 평가 Dataset 계약 | [Agent 평가 Dataset 계약](07-langgraph-agent/05-agent-evaluation-dataset-contract.md) |
| 법령 원문의 출처와 재수집 방법 | [법령 데이터 안내](../data/laws/README.md) |

RAG의 24문항 결과는 개발·회귀 기준선입니다. Agent 전체 품질을 대표하는 최종
성능 점수로 사용하지 않으며, Agent 평가 Dataset은 Tool 호출과 멀티턴 동작을
검증하기 위한 계약·fixture 단계입니다.

## 설계와 구현 기록

| 주제 | 문서 |
| --- | --- |
| 법령 corpus·임베딩·벡터 저장소 선택 | [RAG ADR](02-langchain-rag/01-adr/) |
| 성능·응답 신뢰성 개선 | [성능 개선 기록](00-performance-improvement/README.md) |
| Agent 확장 설계와 Tool 경계 | [LangGraph Agent 문서](07-langgraph-agent/) |
| CI/CD와 실행 환경 | [CI/CD 문서](08-ci-cd-pipeline/README.md) |
| 기존 Next.js UI 기준선 | [기존 UI 문서](09-frontend/02-nextjs-chat-ui.md) |
| 현재 프론트엔드의 배경·상담 화면 기록 | [frontend 문서](../frontend/docs/) |

## 읽는 순서

처음 코드를 읽는 경우에는 **법령 데이터 안내 → RAG 파이프라인 → Agent 평가 Dataset
계약 → 현재 UI 문서** 순서를 권장합니다. 특정 개선의 배경과 비교 결과가 필요할 때만
성능 개선·LangSmith·회고 문서를 참고합니다.

## 문서 관리 기준

- README에는 현재 코드와 직접 확인한 실행 방법만 둡니다.
- 실험 수치에는 Dataset·corpus·모델·주요 설정을 함께 기록합니다.
- 아직 구현 또는 측정하지 않은 항목은 완료처럼 쓰지 않고, 해당 단계 문서에서
  다음 작업으로 구분합니다.
