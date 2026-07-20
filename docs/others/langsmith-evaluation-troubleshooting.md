# LangSmith Dataset 평가 문제 해결

처음 Dataset과 Experiment를 연결하면서 화면이 예상과 다르게 보였던 원인과 해결
방법을 정리한다. 같은 문제가 다시 생겼을 때 Dataset을 새로 만들기 전에 확인할
내용만 남긴다.

## Application 목록에서 Dataset이 사라짐

### 증상

스크립트가 출력한 직접 주소에서는 Dataset과 Experiment가 열렸지만,
`korean-chatbot-rag-dev` Application의 `Datasets & Experiments` 목록에서는 보이지
않았다. 새로고침하면 다시 빈 화면이 나타났다.

### 원인과 해결

Dataset 생성 실패가 아니라 `Application: korean-chatbot-rag-dev` 리소스 태그가
연결되지 않은 상태였다.

1. `Settings > Resource tags`에서 `Application`을 연다.
2. `korean-chatbot-rag-dev` 값의 편집 버튼을 누른다.
3. `Datasets`에서 `korean-chatbot-rag-v1-dev`를 선택한다.
4. Application의 `Datasets & Experiments`에서 새로고침 후에도 보이는지 확인한다.

SDK 생성 성공과 Application 화면 노출은 별도 확인 항목이다. 목록에서 보이지 않을
때는 Dataset을 중복 생성하기 전에 리소스 태그부터 확인한다.

## Reference Outputs에 날짜만 보임

### 증상

Reference Outputs 열에 `2026-07-06`만 보여 Dataset 등록일처럼 보였다. 실제로는
법령 원문을 수집한 corpus snapshot 날짜였다.

### 원인과 해결

기대 답변, 정답 조문, snapshot을 모두 Reference Outputs에 넣어 표에서 첫 값만
두드러져 보였다. 역할을 다음처럼 분리했다.

- Reference Outputs: 사람이 바로 읽을 `reference_answer`
- `metadata.rubric`: 필수·보조 정답 조문, 필수·금지 주장, 지표 적용 여부
- `metadata.corpus_snapshot`: 평가가 참조한 법령 원문 기준일

`register_evaluation_dataset.py`를 다시 실행하면 고정된 example ID를 사용해 기존
24문항을 갱신한다. 평가 질문의 생성일과 corpus snapshot은 서로 다른 정보다.

## 24 runs인데 Judge 점수가 일부 없음

### 증상

전체 평가 진행률은 `24 / 24 runs`였지만 일부 문항의 Faithfulness가 없고 evaluator
trace에 `429 RESOURCE_EXHAUSTED`가 표시됐다.

### 원인

24 runs는 현재 RAG target이 24문항을 실행했다는 뜻이다. Gemini Judge 호출 완료
횟수까지 보장하지 않는다. 검색 평가 대상이 아닌 9문항의 `No Feedback`은 정상적인
`N/A`지만, 평가 대상 문항의 429는 실패다.

Gemini 한도는 API 키가 아니라 Google Cloud 프로젝트 단위다. RPM·TPM·RPD 중 어느
항목을 넘었는지 오류와 AI Studio 사용량 화면에서 확인한다. 일일 요청 한도는 공식
문서 기준 태평양 시간 자정에 초기화된다.

### 확인 순서

1. Experiment의 24개 RAG run에 실행 오류가 없는지 확인한다.
2. 검색 대상 15문항에 Precision·Recall이 모두 있는지 확인한다.
3. 같은 15문항에 Faithfulness가 모두 있는지 확인한다.
4. `No Feedback` 9문항이 Dataset의 `retrieval_eligible=false` 문항과 일치하는지
   확인한다.
5. 세 조건을 만족한 Experiment만 기준선으로 사용한다.

먼저 10문항과 14문항으로 나눠 평가 흐름을 확인했다. 한도가 초기화된 뒤 24문항을
다시 실행해 RAG 오류 0건, 평가 대상 15문항의 검색·Faithfulness 점수 15건을 모두
확인했고 이 실행을 최종 기준선으로 정했다. 앞선 실패 기록은 평가 코드 오류가 아니라
Judge quota와 완료 조건을 구분하게 된 사례로 남겼다.

참고:

- [LangSmith resource tags](https://docs.langchain.com/langsmith/set-up-resource-tags)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
