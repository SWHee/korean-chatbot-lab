# LangChain 첫 기준선 평가 문제 해결

- 작성일: 2026-07-21

첫 24문항 기준선을 만들면서 화면만 보고는 구분하기 어려웠던 문제를 정리한다. 다시 평가할 때 같은 실수를 반복하지 않도록 증상, 원인, 확인 방법만 간단히 남긴다.

## Reference Outputs에 날짜만 보임

### 증상

LangSmith 표의 Reference Outputs에 기대 답변 대신 `2026-07-06`만 먼저 보였다.

### 원인과 해결

이 날짜는 Dataset 등록일이 아니라 평가에 사용한 법령 원문의 기준일이다. 기대 답변,
정답 조문, 원문 기준일을 한곳에 넣어 표에서 날짜가 가장 먼저 보인 것이었다.

역할을 다음과 같이 나눠 다시 등록했다.

- Reference Outputs: 사람이 바로 읽을 `reference_answer`
- metadata의 rubric: 정답 조문과 필수·금지 주장
- metadata의 corpus snapshot: 법령 원문 기준일

이후 Reference Outputs에서는 기대 답변을 먼저 확인하고, 세부 채점 기준은 metadata에서
확인할 수 있게 됐다.

## No Feedback이 모두 오류는 아님

### 증상

24문항 중 일부 문항에는 검색 점수나 Faithfulness 대신 `No Feedback`이 표시됐다.

### 원인과 확인

현재 법령 원문으로 정답 조문을 정할 수 없는 9문항은 검색 평가 대상이 아니다. 이
문항의 `No Feedback`은 의도한 `N/A`다. 반면 평가 대상 문항에서 점수가 없다면 Judge
호출 실패 여부를 확인해야 한다.

구분 기준은 다음과 같다.

| 상황 | 의미 |
| --- | --- |
| 평가 제외 9문항의 No Feedback | 정상, 현재 corpus로 채점하지 않음 |
| 평가 대상 15문항의 No Feedback | 오류 가능성, evaluator trace 확인 필요 |

## 24 runs인데 Judge 점수가 일부 없음

### 증상

Experiment 진행률은 `24 / 24 runs`였지만 일부 Faithfulness 점수가 비어 있었고,
evaluator trace에는 `429 RESOURCE_EXHAUSTED`가 표시됐다.

### 원인

`24 / 24 runs`는 RAG가 24개 질문에 답변했다는 뜻이다. Gemini Judge가 모든 답변을
채점했다는 뜻은 아니다. 당시에는 무료 API 호출 한도에 도달해 일부 Judge 요청이
실패했다.

### 해결

먼저 10문항과 14문항으로 나누어 전체 평가 흐름을 확인했다. API 한도가 초기화된 뒤
24문항을 다시 실행했고, RAG 오류와 Judge 오류가 없는 Experiment를 최종 기준선으로
선택했다.

## 분할 실행과 최종 기준선의 차이

10문항·14문항 실행은 긴 로컬 실행과 API 한도를 나눠 확인하기 위한 중간 점검이었다.
두 실행을 더해 결과를 이해할 수는 있지만 LangSmith에서는 서로 다른 Experiment다.

최종 비교 기준은 다음 조건을 만족한 단일 24문항 Experiment로 정했다.

- 질문 24개가 중복과 누락 없이 실행됨
- RAG 실행 오류 0건
- 검색 평가 대상 15문항의 Precision과 Recall 존재
- 같은 15문항의 Faithfulness 존재
- 평가 제외 9문항의 No Feedback이 Dataset 설정과 일치

## Faithfulness의 `Evaluator run failed`

### 증상

2026-07-27 전체 평가 중 일부 Faithfulness trace에 `Evaluator run failed`와
`503 UNAVAILABLE`이 표시됐다. 같은 실행의 Precision과 Recall은 정상적으로
계산됐다.

### 원인과 구분

확인한 오류 메시지는 Gemini Judge 모델의 일시적인 높은 요청량이었다. RAG 답변 생성,
검색, Faithfulness 판정 로직이나 구조화 출력 parser가 실패한 것은 아니다.

| 표시 | 의미 |
| --- | --- |
| 평가 제외 문항의 점수 없음 | Dataset 기준에 따른 정상 `N/A` |
| `503 UNAVAILABLE` | Judge 서비스가 일시적으로 채점하지 못함 |
| schema·입력 Key 오류 | 평가 코드 수정이 필요한 실패 |

### 처리

Judge SDK의 재시도 횟수를 명시하고, 그 재시도가 끝난 `ServerError`를 지수 간격으로
한 번 더 재시도한다. 그래도 503이면 임의 점수를 만들지 않고 `score=None`과
`재평가 필요` 설명을 Feedback에 남긴다. 503이 아닌 서버 오류와 코드 오류는 원인을
숨기지 않도록 다시 발생시킨다.

이 처리는 평가 결과의 누락을 점수로 바꾸는 방법이 아니다. 일시 장애와 평가 대상
제외를 기록으로 구분하고, 최종 비교에 사용할 Experiment에서는 평가 대상 문항을
다시 채점하기 위한 장치다.

## 다음 평가 전 확인 순서

1. Ollama와 로컬 인덱스가 준비됐는지 확인
2. 처음에는 문항 하나로 target과 evaluator 동작 확인
3. 전체 실행 후 `24 / 24 runs` 확인
4. 평가 대상 15문항의 세 점수 확인
5. evaluator trace에 429나 다른 오류가 없는지 확인
6. 조건을 모두 만족한 Experiment만 기준선으로 지정

이번 경험에서 가장 중요한 점은 실행 완료와 채점 완료가 다르다는 것이다. 진행률만
보지 않고, 평가 대상 문항에 실제 점수가 모두 들어왔는지까지 확인해야 기준선으로
사용할 수 있다.

참고:

- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Gemini API 오류 해결 가이드](https://ai.google.dev/gemini-api/docs/troubleshooting)
- [LangChain Google Generative AI 통합](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai)
