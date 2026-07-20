# LangSmith 추적과 평가 흐름

LangSmith는 현재 RAG가 어떤 순서로 실행됐는지 확인하고, 같은 Dataset으로 변경
전후를 비교하는 데 사용한다. 이 프로젝트에서는 trace 확인과 Dataset 평가를
순서대로 연결했다.

## Trace에서 보는 것

`/ask-rag` 요청 한 건은 다음 흐름으로 처리된다.

```text
사용자 질문
  → KURE-v1 질문 임베딩
  → Chroma 조문 검색
  → 검색 문맥 구성
  → LCEL prompt · Ollama 생성
  → 답변과 출처 반환
```

LangSmith에서는 입력 질문, prompt에 들어간 문맥, 생성 답변과 단계별 시간을 본다.
답변이 이상할 때 검색 조문부터 틀렸는지, 조문은 맞지만 생성 모델이 잘못 해석했는지
나눠 확인하는 것이 목적이다.

## 기본 연결

로컬 `.env`에 다음 값을 둔다.

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<발급받은 키>
LANGSMITH_PROJECT=korean-chatbot-rag-dev
```

FastAPI 서버는 시작할 때 `.env`를 읽는다. 서버를 실행하고 `/ask-rag`를 호출하면
`korean-chatbot-rag-dev`의 Tracing 화면에서 실행을 확인할 수 있다.

```bash
uv run fastapi dev

curl -X POST http://127.0.0.1:8000/ask-rag \
  -H "Content-Type: application/json" \
  -d '{"question":"은행이 파산하면 내 예금은 얼마까지 보호받나요?"}'
```

서버가 꺼지면 새 요청이 없으므로 trace도 더 생기지 않는다. 이미 전송된 trace와
Experiment는 LangSmith 웹에 남는다.

## Dataset 평가 연결

현재 연결은 LangSmith 공식 흐름과 같은 네 단계다.

| 개념 | 현재 프로젝트 |
| --- | --- |
| Dataset | `rag-v1-dev.jsonl`의 24문항 |
| Target | KURE·Chroma·Ollama RAG를 실행하는 `run_rag_evaluation()` |
| Evaluator | 조문 검색 Precision·Recall, Gemini Faithfulness |
| Experiment | Dataset을 현재 RAG로 실행한 한 번의 결과 묶음 |

OpenAI quickstart 예제의 모델과 패키지를 그대로 사용하지 않는 이유는 생성 모델이
로컬 Ollama이고 Judge가 Gemini이기 때문이다. 평가 개념은 같고 구현체만 프로젝트에
맞게 바뀐다.

### Dataset 등록

```bash
uv run python scripts/register_evaluation_dataset.py
```

질문은 Inputs, `reference_answer`는 Reference Outputs로 등록한다. 정답 조문과 지표
적용 여부는 웹 표를 복잡하게 만들지 않도록 example의 `metadata.rubric`에 둔다.

### 한 문항 확인

```bash
uv run python scripts/run_rag_evaluation.py --question-ids A1
```

처음에는 입력, 답변, 검색 출처와 세 평가 Feedback이 보이는지만 확인한다. 모델과
인덱스를 모두 사용하는 평가이므로 FastAPI 서버는 필요 없지만 Ollama는 실행 중이어야
한다.

### 선택 문항 또는 전체 실행

```bash
uv run python scripts/run_rag_evaluation.py --question-ids A1 A2 A3 A4 A5
uv run python scripts/run_rag_evaluation.py --all
```

`max_concurrency=1`로 한 요청씩 실행한다. 로컬 모델 부하를 줄이려면 문항 ID를 여러
묶음으로 나눌 수 있다. 두 실행을 비교할 때는 Dataset, 모델, prompt, 검색 설정과
evaluator를 동일하게 유지한다.

## 현재 기준선

LangChain v1은 단일 Experiment에서 24문항을 평가했다. 누락과 실행 오류가 없고,
평가 대상 15문항의 검색 점수와 Faithfulness가 모두 존재하는 이 실행을 기준선으로
사용한다. 앞선 분할 실행과 한도 실패 실행은 비교·트러블슈팅 기록으로 남긴다.

결과는 [`langchain-baseline-results.md`](../evaluation/langchain-baseline-results.md),
연결 중 겪은 문제는
[`langsmith-evaluation-troubleshooting.md`](langsmith-evaluation-troubleshooting.md)에
분리해 기록한다.

공식 문서:

- [LangSmith observability](https://docs.langchain.com/langsmith/observability)
- [Trace with LangChain](https://docs.langchain.com/langsmith/trace-with-langchain)
- [Evaluation quickstart](https://docs.langchain.com/langsmith/evaluation-quickstart)
