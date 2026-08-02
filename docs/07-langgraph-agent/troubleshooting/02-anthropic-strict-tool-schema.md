# Anthropic strict Tool schema의 숫자 범위 오류

## 증상

법령 Tool 하나만 바인딩한 Claude 호출은 성공했지만, 숫자 필드가 있는 상품 Tool을
함께 바인딩하자 API가 다음 400 오류를 반환했다.

```text
For 'integer' type, property 'minimum' is not supported
```

## 원인

상품 입력 모델의 `Field(ge=1)`이 JSON Schema의 `minimum: 1`로 변환됐다. Anthropic의
strict Tool Calling은 입력 자료형을 강제하지만 전체 JSON Schema가 아닌 지원되는
일부 형식만 허용한다. 현재 strict schema에는 `minimum`을 보낼 수 없었다.

## 선택과 적용

strict 모드를 끄면 이름과 인자 자료형 보장이 약해지므로 유지했다. 대신 API에 보내는
schema에는 `integer`와 설명만 남기고, `term_months`와 `limit`이 1 이상인지 확인하는
값 검증은 Pydantic validator로 옮겼다.

이렇게 책임을 나눴다.

- Anthropic strict schema: Tool 이름, 필수 필드, 자료형, enum 보장
- 프로젝트 Pydantic 검증: 지원되지 않는 숫자 범위 보장

## 확인

- 생성 schema에 `minimum`이 없는지 자동 테스트
- `0` 입력을 로컬 Pydantic 검증이 거부하는지 자동 테스트
- 실제 Claude API로 법령 Tool, 상품 Tool, Tool 미사용 질문 확인

수정 후 상품 Tool은 `deposit`, `12개월`, `base_interest_rate`, `3개`를 올바른 인자로
반환했고, 인사에는 빈 `tool_calls`를 반환했다. 이 단계에서는 호출 요청만 확인했으며
Tool 실행과 결과 전달은 12단계에서 다룬다.
