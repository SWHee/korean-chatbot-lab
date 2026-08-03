# Agent SSE의 Claude 콘텐츠 블록 누락

## 증상

Next.js에서 `12개월 금융상품 추천`에 이어 `적금으로 찾고 있습니다`라고 입력하면
`Agent가 빈 응답을 보냈습니다.`가 표시됐다. 같은 Agent를 Swagger에서 실행하면
추가 질문이나 최종 답변은 확인할 수 있었다.

## 원인

실제 SSE에는 분석과 Tool 실행, 최종 `result`가 있었지만 `token`이 없었다. Claude의
최종 응답 조각이 문자열이 아니라 다음 콘텐츠 블록으로 전달됐기 때문이다.

```python
[{"text": "답변", "type": "text", "index": 0}]
```

Graph는 `chunk.content`가 문자열일 때만 token을 보냈고, UI는 token만 답변으로
누적했다. 따라서 백엔드의 최종 답변은 존재했지만 화면에서는 빈 답변으로 판단했다.
API도 콘텐츠 블록에 `str()`을 적용해 리스트 표현을 answer로 반환하고 있었다.

## 고려한 선택지

| 선택지 | 판단 |
| --- | --- |
| Prompt로 문자열 응답만 요구 | 모델 응답 형식을 코드 계약으로 보장할 수 없음 |
| UI에서 최종 result만 표시 | 빈 화면은 막지만 실제 token 누락과 잘못된 API answer가 남음 |
| Graph·API에서 표준 text를 사용하고 UI에 result 안전장치 추가 | 원인을 생성 경계에서 고치고 화면도 복구 가능 |

세 번째 방법을 선택했다. LangChain 메시지가 문자열과 콘텐츠 블록을 공통으로
변환하는 `message.text`를 사용하고, UI는 token이 하나도 없을 때만 최종
`result.answer`를 사용한다. 정상 스트리밍에서는 기존 token 누적을 유지한다.

## 적용과 확인

- Claude 형태의 콘텐츠 블록이 token으로 전달되는 Graph 회귀 테스트 추가
- 최종 Agent answer가 리스트 표현이 아닌 자연어가 되는 API 회귀 테스트 추가
- Next.js의 result answer fallback과 프로덕션 빌드 확인
- 실제 두 턴 요청에서 `analyze → tools → generate → token → result` 확인

수정 후 두 번째 턴은 빈 응답 오류 없이 Claude 답변 조각과 최종 자연어 answer를
반환했다.

재현 과정에서 적금 Tool은 `unsupported`도 반환했다. 현재 POC는 적금 원본 API 호출만
있고 정규화·비교는 정기예금만 지원하므로 이는 별도 기능 범위다. 적금 비교를 구현하기
전에는 정기예금 지원 범위를 UI와 추가 질문에서 분명하게 안내해야 한다.

Claude가 Tool 호출 직전에 짧은 안내 문장을 생성하는 경우도 확인했다. 현재는 이 조각과
Tool 실행 후 최종 답변이 모두 token이므로 화면에서 이어질 수 있다. 빈 응답과는 다른
문제로, 이후 이벤트 계약에서 Tool 선택 중 문장과 최종 답변을 구분해 다룬다.
