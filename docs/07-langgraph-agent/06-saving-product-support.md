# 적금 상품 지원 설계와 작업 기록

## 문제

Agent의 상품 입력 계약은 `deposit`과 `saving`을 모두 허용하고 적금 Finlife
endpoint 호출도 검증했다. 하지만 실제 상품 Tool은 정기예금만 정규화·비교하므로
적금 질문에 `unsupported`를 반환한다.

이번 작업의 목표는 새로운 그래프 경로를 만드는 것이 아니다. 정기예금과 나란히
적금 처리기를 추가해, 사용자가 기간을 제시하면 Finlife 적금 공시 후보를 같은 Agent
대화 흐름에서 확인할 수 있게 하는 것이다.

## 선택지와 결정

| 선택지 | 장점 | 한계 | 결정 |
| --- | --- | --- | --- |
| 적금을 예금 모델로 변환 | 수정량 최소 | 적립 방식 유실, 모델 이름과 의미 불일치 | 제외 |
| 적금 모델·처리기 분리 | 현재 구조 보존, 적금 고유 필드 유지 | 유사 코드 일부 증가 | 선택 |
| 전체 상품 모델 공통화 | 장기 확장에 유리 | 현재 예·적금 범위보다 수정이 큼 | 이후 검토 |

적금은 정기예금과 공통 필드가 많지만 `rsrv_type`, `rsrv_type_nm`으로 적립 방식을
구분한다. 따라서 외부 API 필드는 각각 `reserve_type`, `reserve_type_name`으로 바꾸고
적금 응답 모델에 보존한다.

## 구현 범위

```text
사용자 적금 질문
  → 기존 멀티턴 조건 확인(product_type=saving, term_months)
  → 기존 search_financial_products Tool
  → 적금 API 호출
  → 적금 기본정보와 기간·금리 옵션 연결
  → 기간·금리 기준 상위 후보 선택
  → Agent 답변과 적금 상품 카드 표시
```

- 적금 전용 응답 모델과 정규화·비교 함수
- 상품 Tool의 `deposit`·`saving` 처리 분기
- Agent API 응답에서 두 상품 타입 보존
- 화면의 예금·적금 제목과 적금 적립 방식 표시
- 고정 응답 기반 단위 테스트와 기존 예금 회귀 테스트

새 Node, Edge, Tool, 패키지, 데이터베이스는 추가하지 않는다. 현재 기능은 개인별
가입 가능성을 판정하는 추천 알고리즘이 아니라, 사용자가 지정한 기간과 금리 기준으로
공시 후보를 비교하는 기능으로 유지한다.

## 완료 기준

- `12개월 적금 추천` 흐름이 `unsupported` 대신 적금 후보 반환
- 정액적립식·자유적립식 정보가 Tool, API, 화면까지 유지
- 기존 정기예금 질문과 법령 질문의 동작 유지
- Finlife 오류와 후보 없음 상태가 기존과 같은 형식으로 반환

## 이후 상품군 확장 판단

예·적금은 기간과 기본·최고금리라는 비교 축을 공유해 각각의 작은 처리기로 유지할 수
있다. 연금저축과 대출은 수익률·보증이율 또는 상환 방식·신용 구간처럼 비교 기준이
달라 같은 모델에 선택 필드를 계속 추가하면 의미가 흐려진다.

세 번째 상품군을 추가할 때는 다음과 같이 재구성하는 편이 자연스럽다.

```text
공통 상품 정보
  ├─ 예·적금 비교 모델
  ├─ 연금저축 비교 모델
  └─ 대출 비교 모델
```

그 시점에는 공통 식별 정보만 상위 계약으로 올리고, 카테고리마다 입력 조건·정렬
기준·설명 책임을 분리한다. 이번 작업에서는 미래 구조를 미리 구현하지 않는다.

## 적용 결과

### 변경

- `SavingProductOption`, `SavingProductComparison`과 적금 정규화·후보 선택 함수를 추가
- 적금 API의 `rsrv_type`, `rsrv_type_nm`을 `reserve_type`, `reserve_type_name`으로 변환
- 기존 `search_financial_products` Tool이 `product_type=saving`이면 적금 처리기를 선택
- Agent API 응답이 `product_type`으로 예금·적금 모델을 구분
- 근거 패널이 `적금 후보` 제목과 적립 방식을 표시하고, 카드 식별값에도 적립 방식을 포함

### 확인

- `uv run pytest -q` → 155 passed, 2 skipped
- `npm test && npm run build` → 11 tests passed, Next.js production build 성공
- `RUN_FINLIFE_LIVE_TEST=1 uv run pytest tests/test_finlife.py::test_fetch_saving_products_live_smoke -q`
  → 실제 Finlife 적금 endpoint 1 passed

### 현재 한계

적립 방식은 결과에 표시하지만, 아직 사용자가 `자유적립식만`처럼 적립 방식을 조건으로
선택하는 기능은 없다. 이는 다음 작은 개선에서 `reserve_type`을 대화 조건과 Tool 입력에
추가해 처리할 수 있다. 현재 기능은 예금과 마찬가지로 상품 유형·기간·금리 기준에 따른
공시 후보 비교다.
