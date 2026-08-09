---
date: 2026-08-09
status: completed
result: Finlife 예·적금 코드를 데이터 계약·API 호출·비교 로직으로 분리
---

# 금융상품 영역 분리

## 문제

`finlife.py` 하나가 예·적금 데이터 모델, 외부 API 호출, 원본 필드 정규화와 후보 정렬까지
맡고 있었다. 상품 종류를 더 추가하면 서로 다른 변경 이유가 한 파일에 계속 쌓일 구조였다.

## 판단

현재 지원 범위인 예금·적금의 동작은 바꾸지 않고 책임만 세 부분으로 나눴다. Agent와 API는
세부 파일을 직접 고르지 않고 `chatbot.products`를 통해 기존 이름을 그대로 사용한다.

## 적용

- `products/models.py`: 예·적금 옵션과 비교 결과 형식
- `products/client.py`: Finlife endpoint와 HTTP 응답 확인
- `products/comparison.py`: 원본 필드 정규화와 금리 기준 후보 선택
- Agent·API import를 `chatbot.products`로 변경

## 결과

예금·적금 조회 Tool의 입력, 반환값, 정렬 기준은 유지된다. 향후 대출처럼 데이터 형식과
비교 기준이 다른 상품은 현재 예·적금 모델과 섞지 않고 별도 영역으로 확장할 수 있다.

검증: Finlife, Agent Tool·멀티턴, API 응답 테스트
