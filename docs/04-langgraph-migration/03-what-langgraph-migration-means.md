# LangGraph로 마이그레이션한다는 의미

- 작성일: 2026-07-22

처음에는 LangChain RAG를 LangGraph로 마이그레이션하면 기존 LCEL 체인 파일을 없애고,
검색부터 prompt 구성과 모델 호출까지 전부 Graph의 Node로 다시 만들어야 한다고
생각했습니다. 실제로는 LangGraph와 LCEL이 담당하는 범위가 다릅니다.

## 처음 생각했던 구조

모든 세부 작업을 Node로 만들면 다음과 같은 Graph를 구성할 수 있습니다.

```text
START
  ↓
retrieve
  ↓
format_context
  ↓
build_prompt
  ↓
call_model
  ↓
parse_output
  ↓
END
```

기술적으로 가능한 구조지만, 항상 붙어서 실행되는 작은 변환까지 Graph의 State와
Edge로 관리해야 합니다. 분기하거나 따로 복구할 필요가 없는 작업까지 Node로 만들면
Graph가 길어지고 전체 흐름을 이해하기 어려워집니다.

## 현재 프로젝트에서 선택한 구조

LangGraph는 검색과 생성이라는 큰 작업 순서와 State를 관리합니다. 생성 Node 안에서는
기존 LCEL의 `prompt | model | parser`를 재사용합니다.

```text
START
  ↓
retrieve
  ↓
generate
  └─ prompt | model | parser
  ↓
END
```

각 계층의 역할은 다음과 같습니다.

| 구분 | 역할 |
| --- | --- |
| LangGraph | State, Node, Edge와 전체 실행 순서 관리 |
| LCEL | 생성 Node 안에서 prompt, model, parser 연결 |
| Retriever | 질문과 가까운 법령 조문 검색 |
| Generator | 구성된 prompt를 Ollama Qwen3에 전달해 답변 생성 |

마이그레이션의 기준은 LangChain 코드가 모두 사라지는지가 아닙니다. 검색과 생성의
최상위 실행 순서를 Graph가 관리하고, 이후 필요한 분기와 반복을 Graph에 추가할 수
있는지가 기준입니다.

## Node로 나누는 기준

다음 질문 중 하나에 해당하면 독립된 Node로 나눌 가치가 있습니다.

- 결과를 State에 저장하고 다음 작업에서 사용해야 하는가?
- 성공과 실패에 따라 다른 경로로 이동해야 하는가?
- 해당 단계만 다시 실행하거나 별도로 관찰해야 하는가?
- 다른 API나 Tool로 교체할 가능성이 있는가?

현재 `retrieve`는 검색 실패와 fallback을 확장할 수 있고, `generate`는 답변 검증과
재생성으로 연결할 수 있으므로 각각 Node로 두었습니다. 반면 prompt 구성과 문자열
parser는 지금 별도로 분기할 이유가 없으므로 생성 Node 안의 LCEL로 유지합니다.

## 현재 코드에 대입하기

- `src/chatbot/graph.py`: `retrieve → generate` 순서와 State 관리
- `src/chatbot/retriever.py`: `retrieve` Node가 재사용하는 법령 검색
- `src/chatbot/rag.py`: `generate` Node가 재사용하는 LCEL 생성 체인
- `src/chatbot/ollama_generator.py`: 실제 Qwen3 생성 요청
- `src/chatbot/main.py`: FastAPI 요청을 Graph 입력과 응답으로 연결

`rag.py`가 남아 있다는 사실은 마이그레이션이 덜 되었다는 뜻이 아닙니다. Graph가
LCEL 생성 체인을 하나의 Node 기능으로 사용하고 있다는 뜻입니다.

## AI Agent까지의 발전 방향

선형 Graph의 동작을 먼저 확인한 뒤, 의미 있는 분기와 Tool을 작은 단위로 추가합니다.

```text
START
  ↓
질문 분석
  ├─ 법령 검색 Tool
  ├─ Finlife 상품 조회 Tool
  ├─ 추가 정보 요청
  └─ 답변 생성
       ↓
     답변 검증
       ├─ 충분함 → END
       └─ 부족함 → 다시 Tool 선택
```

작업 순서는 다음과 같습니다.

1. 현재 선형 StateGraph를 FastAPI와 스트리밍에 연결
2. 같은 Dataset으로 기존 LangChain 기준선과 동작 비교
3. Finlife API 단독 호출을 확인하고 상품 조회 Node 추가
4. 법령·상품·혼합 질문을 나누는 조건부 Edge 추가
5. 모델이 필요한 Tool을 선택하고 결과가 부족하면 반복하는 Agent로 확장
6. 같은 Dataset과 Evaluator로 변경 전후 결과 비교

핵심은 모든 함수를 Node로 바꾸는 것이 아니라, 상태·분기·반복이 필요한 작업을
Node로 올리고 그 안의 작은 처리에는 기존 함수와 LCEL을 재사용하는 것입니다.
