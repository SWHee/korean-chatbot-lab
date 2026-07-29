# README 최신 베이스라인

- 작성일: 2026-07-29
- 상태: 현재 구현을 반영한 공개 문서 기준선
- 다음 갱신: Finlife Client POC가 실제 코드와 테스트로 완료된 뒤

## 목적

프로젝트 README가 작업 순서를 나열하는 학습 기록보다, 처음 방문한 사람이 현재
기능과 실행 방법을 빠르게 이해하는 공개 문서 역할을 하도록 기준을 정리했다.

README에는 현재 코드·테스트·평가로 확인한 사실만 남기고, 아직 구현하지 않은
기능은 현재 상태와 로드맵에서 분리해 표시한다.

## 적용한 구성

- 기존 상담 UI 심볼을 확장한 가로형 히어로 이미지
- Python, FastAPI, LangChain, LangGraph, Ollama, Next.js 기술 배지
- 프로젝트 소개, 핵심 기능과 영역별 구현 상태
- 현재 실행 가능한 RAG 아키텍처와 데이터 흐름
- backend, 모델, 인덱스와 Next.js 실행 순서
- JSON·스트리밍 API 예시
- 24문항 LangChain·LangGraph 회귀평가 결과
- Finlife Client부터 Agent까지의 다음 구현 순서
- 처음 읽을 핵심 문서 링크

히어로 이미지는 `docs/assets/readme-hero.png`에 두고, frontend에서 사용하는
`frontend/public/financial-guardian.png`는 변경하지 않았다. 이미지 안에는 버전이나
기술 이름을 넣지 않아 README의 배지와 본문에서 실제 상태에 맞게 관리한다.

## 현재 프로젝트 상태

| 구분 | 현재 기준 |
| --- | --- |
| 법령 데이터 | 금융소비자보호법·예금자보호법과 각 시행령 4건 |
| 검색 인덱스 | 260개 조문, 322개 청크 |
| 실행 흐름 | LangGraph `retrieve → generate` |
| 생성 | Ollama Qwen3 Structured Output |
| API | FastAPI JSON·텍스트 스트리밍 |
| 화면 | Next.js 상담 UI와 FastAPI proxy |
| 회귀평가 | 24문항, 실행 오류 0건 |
| 다음 기능 | Finlife 은행권 정기예금 1페이지 client |

## Workflow와 Agent 표현 기준

현재 `src/chatbot/graph.py`의 Graph는 다음 순서로 실행된다.

```text
START → retrieve → generate → END
```

두 Node의 순서가 코드에 고정되어 있으므로 현재 단계는 LangGraph를 사용한
Workflow다. 모델이 Tool 사용 여부나 다음 실행을 선택하지 않기 때문에 완성된
AI Agent라고 표현하지 않는다.

프로젝트는 다음 경계를 차례로 확인하며 하나의 AI Agent로 발전한다.

1. Finlife 상품 조회 client와 정규화
2. 상품 Node와 법령·상품 조건부 경로
3. 자연어 질문을 route와 조회 입력으로 바꾸는 분석 Node
4. 법령·상품·혼합 질문을 처리하는 Routed Workflow
5. 모델이 두 Tool과 반복 종료를 선택하는 tool-calling loop
6. Agent 전용 Dataset과 비스트리밍 API

세부 입력·출력과 단계별 완료 조건은
[`Finlife에서 LangGraph Agent까지의 실행 명세`](../07-langgraph-agent/01-finlife-agent-expansion-spec.md)를
기준으로 삼는다.

## README 갱신 기준

- 완료 표시는 제품 코드와 직접 검증 결과가 모두 있을 때만 사용
- 새로운 기술 배지는 실제 의존성과 주력 실행 경로에 들어온 뒤 추가
- 평가 수치는 Dataset, 모델, corpus와 설정이 같은 비교 결과만 갱신
- 계획이 바뀌면 README의 현재 상태와 로드맵을 함께 수정
- 상세한 실패·비교 기록은 README에 누적하지 않고 해당 단계 문서에 보관

## 확인 결과

- README가 참조하는 로컬 파일 누락 0건
- backend pytest 66건 통과
- Next.js production build와 TypeScript 검사 통과
- 기존 Docker·CI/CD 작업 파일은 이번 기준선 범위에서 제외
