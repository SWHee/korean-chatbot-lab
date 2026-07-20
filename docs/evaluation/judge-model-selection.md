# LLM Judge 모델 선택

- 조사일: 2026-07-15
- 결정: `gemini-3.5-flash`
- 적용 범위: LangChain v1 기준선의 Faithfulness 15문항

## Judge가 맡는 역할

Judge는 법률 정답을 새로 만드는 모델이 아니다. 현재 구현은 RAG의 질문, 실제 검색
문맥, 생성 답변을 보고 다음 두 가지를 확인한다.

- 답변의 사실 주장이 검색 문맥에서 확인되는가
- 검색 문맥에 없거나 문맥과 모순되는 주장을 만들지 않았는가

질문에 충분히 답했는지, 최신 상품을 안내했는지, 범위 밖 질문을 알맞게 처리했는지는
현재 Faithfulness에 포함하지 않는다. 검색 Precision과 Recall도 코드에서 조문 ID로
직접 계산하므로 Judge에게 다시 맡기지 않는다.

## 선택할 때 본 조건

1. 한국어 법령 문장과 답변을 읽을 수 있는가
2. `score`, `reason`, `issues` 구조를 안정적으로 반환하는가
3. 24문항 POC를 무료 API 범위에서 실행할 수 있는가
4. LangGraph 전환 후에도 같은 모델과 기준을 유지할 수 있는가
5. 공개 법령과 학습용 질문을 전송해도 되는가

현재 Dataset에는 공개 법령과 가상 질문만 있다. 실제 사용자의 자산·개인 조건이
들어오면 무료 API에 보내기 전에 데이터 이용 조건을 다시 확인해야 한다.

## 검토한 후보

| 후보 | 장점 | 주의점 |
| --- | --- | --- |
| Gemini 3.5 Flash | 한국어 이해, 구조화 출력, 무료 tier | 프로젝트별 호출 한도 확인 필요 |
| Gemini 2.5 Flash | 익숙한 API와 구조화 출력 | 이번 기준선에서는 같은 조건으로 실측하지 않음 |
| Gemini 3.1 Flash-Lite | 무료 반복 평가에 유리 | 법령 조건과 모순을 구분하는 품질을 별도 확인해야 함 |
| Groq GPT-OSS 120B | 다른 모델 계열로 교차 확인 가능 | 무료 token 한도로 전체 반복 평가가 어려울 수 있음 |

첫 기준선은 현재 환경에서 호출과 구조화 출력이 정상 동작한 Gemini 3.5 Flash로
정했다. LangGraph 비교에서도 Judge 모델과 prompt를 그대로 유지한다. 모델을 바꾸면
RAG가 아니라 채점자의 변화까지 점수에 섞이기 때문이다.

## 출력과 점수

Judge는 세 필드만 반환한다.

| 필드 | 의미 |
| --- | --- |
| `score` | `0`, `0.5`, `1` 중 하나인 Faithfulness 점수 |
| `reason` | 해당 점수를 준 핵심 이유 |
| `issues` | 문맥에 없거나 문맥과 모순되는 주장, 최대 3개 |

세 단계 점수를 사용한 이유와 A1 판정 사례는
[`faithfulness-scoring.md`](faithfulness-scoring.md)에 별도로 기록한다.

## 실행 결과

LangChain v1 기준선은 단일 Experiment에서 24문항을 실행했다. 검색과 Faithfulness
평가 대상 15문항 모두 Gemini 점수가 남았고 평균은 `0.733`이었다. 이 값은 현재 검색
문맥에 대한 충실도일 뿐, 전체 답변 정답률은 아니다.

Gemini 무료 한도는 API 키가 아니라 Google Cloud 프로젝트 단위로 적용된다. 공식
문서에 따르면 일일 요청 한도는 태평양 시간 자정에 초기화된다. 한도 오류가 발생하면
새 키를 만들기보다 AI Studio의 프로젝트 사용량과 오류에 표시된 RPM·TPM·RPD 항목을
먼저 확인한다.

참고:

- [Gemini API 구조화 출력](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Gemini API 가격](https://ai.google.dev/gemini-api/docs/pricing)
