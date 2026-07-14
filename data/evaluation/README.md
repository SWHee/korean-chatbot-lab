# RAG 평가 데이터

`rag-v1-dev.jsonl`은 현재 LangChain 법령 RAG의 개발·회귀 평가용 Dataset이다.
질문과 정답 문장만 저장하지 않고, 검색과 생성 품질을 따로 확인할 수 있도록
정답 조문과 답변 조건도 함께 둔다.

## 법령 인덱스와 평가 Dataset의 차이

둘은 역할이 다르다.

| 구분 | 저장 위치 | 들어 있는 데이터 | 역할 |
| --- | --- | --- | --- |
| 법령 원문 | `data/laws/*.xml` | 법령 4건의 XML snapshot | 인덱싱의 원본 |
| Chroma 인덱스 | `data/index/` | 법령 청크의 1024차원 벡터와 메타데이터 | 질문과 가까운 조문 검색 |
| 평가 Dataset | `data/evaluation/rag-v1-dev.jsonl` | 질문, 정답 조문, 기대 답변 조건 | 검색·답변 품질 채점 |

평가 Dataset 자체를 Chroma에 넣는 것은 아니다. Dataset의 질문을 RAG에 입력하고,
RAG가 기존 Chroma 인덱스에서 어떤 조문을 찾고 어떤 답변을 만드는지 확인한다.

```text
평가 질문 1개
  → Chroma에서 법령 조문 검색
  → 검색된 조문을 근거로 답변 생성
  → gold 조문·답변 조건과 비교해 점수 계산
```

## 데이터 출처

- 질문: `docs/evaluation/rag-questions.md`에서 정리한 24개 질문
- 법령 근거: `data/laws/`의 2026-07-06 국가법령정보 Open API snapshot
- gold 조문과 기대 주장: 법령 XML 원문 대조 후 작성

이 질문 중 15개는 임베딩 모델 선정과 검색 검증에 이미 사용했다. 따라서 이 파일은
LangGraph 전후의 회귀를 확인하는 `dev` split이며, 독립적인 최종 성능을 주장하는
test split이 아니다. held-out test는 현재 기준선을 만든 뒤 별도 버전으로 추가한다.

## 주요 필드

| 필드 | 의미 |
| --- | --- |
| `id` | A1처럼 유형 문자와 순번을 합친 질문 ID |
| `primary_gold_articles` | 질문에 답하는 데 꼭 필요한 조문 |
| `supporting_gold_articles` | 함께 검색되면 도움이 되는 보조 조문 |
| `reference_answer` | 정답 문장 복사본이 아니라 기대 답변의 기준 |
| `required_claims` | 답변에 포함해야 하는 핵심 주장 |
| `forbidden_claims` | 오래된 정보, 과장, 근거 없는 단정처럼 피해야 하는 주장 |
| `metric_eligibility` | 질문별로 적용할 수 있는 RAG 평가 지표 |

JSONL은 한 줄에 질문 하나를 저장한다. 각 줄은 JSON 객체이며 문자열, 참·거짓,
목록, 객체를 함께 사용한다.

| 필드 | 데이터 유형 | 예시 |
| --- | --- | --- |
| `id`·`question` | 문자열 | `"A1"`, `"은행이 파산하면..."` |
| `retrieval_eligible` | 참·거짓 | `true` |
| `primary_gold_articles` | 객체 목록 | 법령명과 조문번호 목록 |
| `required_claims` | 문자열 목록 | 답변에 필요한 핵심 내용 목록 |
| `metric_eligibility` | 참·거짓 값을 가진 객체 | 지표별 적용 여부 |

`id`는 파일의 줄 번호가 아니라 질문의 고정 이름이다. 질문 순서가 바뀌어도 A1이라는
이름을 유지하므로, 여러 실험에서 같은 질문의 결과를 비교할 수 있다.

Context Recall은 `primary_gold_articles`와 `required_claims`를 기준으로 필수 근거를
놓쳤는지 확인한다. Context Precision은 primary와 supporting 조문을 모두 관련
문맥으로 인정해 검색 순위를 평가한다.

A5, B2, B3처럼 현행 조문 인덱스만으로 직접 답하기 어려운 질문에는 검색 점수를
억지로 계산하지 않는다. D·E 유형도 검색 정답보다 범위 안내가 중요한 질문이라
Answer Relevancy와 별도 행동 rubric으로 평가한다.

## 다음 평가 단계에서 필요한 출력

평가용 함수는 질문 하나를 받아 다음 세 가지를 돌려줘야 한다.

- `answer`: 로컬 생성 모델의 최종 답변
- `sources`: 검색된 법령명·조문번호·시행일
- `retrieved_contexts`: 생성 모델에게 실제로 제공한 조문 본문 목록

여기서 평가용 함수는 **채점할 대상 프로그램을 한 번 실행하는 함수**라는 뜻이다.
LangSmith 문서에서는 이를 `target`이라고 부른다. 일반 `/ask-rag` 응답에는 조문
본문이 없지만, 평가할 때는 답변이 근거를 지켰는지 확인해야 하므로 내부 결과에
본문을 함께 보존한다.

## 아직 만들지 않은 held-out test

held-out test는 **모델·검색 설정을 고를 때 한 번도 사용하지 않고 마지막에만 여는
새 시험 문제**다. 현재 24문항은 이미 임베딩 선정과 검색 검증에 사용했으므로 개발·회귀
비교에는 유용하지만 독립적인 최종 성능 수치로 사용하지 않는다.

현재 Dataset으로 평가 코드와 기준선을 먼저 완성한 뒤, 새 질문 10~12개를 별도
test split으로 만들고 이후 설정 변경에 사용하지 않는다.
