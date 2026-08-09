# 핀봄의 LangGraph Agent

핀봄의 Agent는 질문에 바로 답하기 전에 현재 의도와 같은 상담에서 확인한 조건을
분석합니다. 답변 가능한 질문은 법령 검색이나 Finlife 상품 조회를 거쳐, 실제 사용한
근거와 답변을 분리해 반환합니다.

![질문을 분석하고 법령·금융상품 근거를 조회하거나 조건 보완과 지원 범위를 안내하는 핀봄 Agent 흐름](../assets/finbom-agent-flow.svg)

> 첫 그림은 전체 구현을 노드 단위로 복제하지 않고, 상담에서 확인할 핵심 경로와 종료
> 분기만 요약합니다. 이어지는 Mermaid 다이어그램은 시스템 요청과 실제 Graph 노드를
> 각각 보완합니다.

## 핵심 흐름

- **질문 분석과 분기:** 질문 의도, 상품 조건과 추가 확인이 필요한 항목을 판단합니다.
- **조건 보완과 범위 안내:** 조건이 부족하면 한 가지만 묻고, 지원하지 않는 질문에는
  가능한 상담 범위를 안내합니다.
- **근거 조회:** 법령 검색과 Finlife 예·적금 조회 결과를 답변 근거로 사용합니다.
- **상담 상태 유지:** 메시지와 확인된 상품 조건을 `thread_id`별 SQLite Checkpointer에
  보존합니다.

## 시스템 흐름

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"transparent","primaryColor":"#EAF2F8","primaryTextColor":"#17324D","primaryBorderColor":"#7EA3C1","lineColor":"#71869A","secondaryColor":"#F4F7FA","tertiaryColor":"#F4F7FA","edgeLabelBackground":"#F4F7FA","fontFamily":"Arial, sans-serif","fontSize":"16px"},"flowchart":{"curve":"basis","nodeSpacing":30,"rankSpacing":42,"padding":24,"htmlLabels":true}}}%%
flowchart TD
    USER["사용자 질문"] --> NEXT["Next.js BFF<br/>/api/chat · 요청 검증과 스트림 중계"]
    NEXT --> API["FastAPI<br/>/ask-agent/stream · Agent 실행"]
    API --> AGENT["LangGraph Agent<br/>질문 분석 · 경로 선택 · 답변 구성"]

    STATE[("SQLite Checkpointer<br/>상담 상태 복원 · 저장")]
    STATE -.-> AGENT

    AGENT --> EVIDENCE["근거 조회<br/>법령 RAG · Finlife 예·적금"]
    AGENT --> EARLY["조건 보완<br/>지원 범위 안내"]
    EVIDENCE --> RESPONSE["응답 조립<br/>answer · sources · products · route"]
    EARLY --> RESPONSE
    RESPONSE --> SSE["SSE event stream<br/>status · token · result"]
    SSE --> UI["핀봄 상담 화면<br/>답변 · 법령 근거 · 비교 상품"]

    classDef entry fill:#F7FAFC,stroke:#9AAFC0,color:#17324D,stroke-width:1.2px;
    classDef service fill:#EAF2F8,stroke:#7EA3C1,color:#17324D,stroke-width:1.3px;
    classDef agent fill:#DCECF8,stroke:#4E83AA,color:#102A43,stroke-width:1.8px;
    classDef evidence fill:#EDF4F7,stroke:#6F9CB5,color:#17324D,stroke-width:1.3px;
    classDef state fill:#F4F7FA,stroke:#93A6B7,color:#334E68,stroke-width:1.2px;
    classDef output fill:#204F73,stroke:#3D769F,color:#FFFFFF,stroke-width:1.5px;
    classDef default font-family:Arial,font-size:16px;

    class USER entry;
    class NEXT,API service;
    class AGENT agent;
    class EVIDENCE evidence;
    class EARLY service;
    class STATE state;
    class RESPONSE,SSE,UI output;
    linkStyle default stroke:#71869A,stroke-width:1.4px;
```

> 여기서 Agentic RAG는 현재 구현처럼 Agent가 근거 Tool 호출 필요 여부를 판단하는 구조를
> 뜻합니다. 질의 재작성이나 검색 결과 자가평가 반복은 이 그래프에 포함하지 않습니다.

## Agentic RAG 노드 구조

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"transparent","primaryColor":"#EAF2F8","primaryTextColor":"#17324D","primaryBorderColor":"#7EA3C1","lineColor":"#71869A","secondaryColor":"#F4F7FA","tertiaryColor":"#F4F7FA","edgeLabelBackground":"#F4F7FA","fontFamily":"Arial, sans-serif","fontSize":"16px"},"flowchart":{"curve":"basis","nodeSpacing":30,"rankSpacing":44,"padding":24,"htmlLabels":true}}}%%
flowchart TD
    START(["START"]) --> ANALYZE["analyze_turn<br/>질문 의도 · 상품 조건 분석"]

    ANALYZE -->|clarify| CLARIFY["ask_clarifying_question<br/>부족한 조건 한 가지 질문"]
    ANALYZE -->|out_of_scope| SCOPE["explain_scope<br/>지원 범위와 예시 안내"]
    CLARIFY --> WAIT["다음 사용자 턴 대기"]
    SCOPE --> WAIT
    WAIT --> EARLY_END(["END"])

    ANALYZE -->|ready| MODEL["agent_model<br/>Tool 선택 또는 최종 답변"]

    subgraph READY_PATH["Agent 실행 경로"]
        direction TB
        MODEL --> BUILD["build_agent_response<br/>답변 · 사용 근거 · 비교 상품"]
        MODEL --> STOP["stop_repeated_call<br/>반복 호출 한도 초과 · 안전 안내"]
        STOP --> BUILD

        MODEL --> RECORD["record_tool_calls<br/>호출 횟수 · 중복 서명 기록"]
        RECORD --> TOOLS["ToolNode<br/>search_law_articles<br/>search_financial_products"]
        TOOLS --> REENTER["agent_model 재진입<br/>조회 결과로 다음 행동 결정<br/>필요하면 Tool 호출 반복 · 최대 4회"]
        REENTER --> BUILD
        BUILD --> ANSWER(["END"])
    end

    classDef boundary fill:#F7FAFC,stroke:#9AAFC0,color:#17324D,stroke-width:1.2px;
    classDef analysis fill:#EAF2F8,stroke:#7EA3C1,color:#17324D,stroke-width:1.4px;
    classDef model fill:#DCECF8,stroke:#4E83AA,color:#102A43,stroke-width:1.8px;
    classDef branch fill:#F4F7FA,stroke:#93A6B7,color:#334E68,stroke-width:1.2px;
    classDef tool fill:#EDF4F7,stroke:#6F9CB5,color:#17324D,stroke-width:1.4px;
    classDef guard fill:#F5F1F2,stroke:#AD8B92,color:#4A3035,stroke-width:1.2px;
    classDef terminal fill:#204F73,stroke:#3D769F,color:#FFFFFF,stroke-width:1.5px;
    classDef default font-family:Arial,font-size:16px;

    class START boundary;
    class ANALYZE analysis;
    class MODEL,REENTER model;
    class CLARIFY,SCOPE,WAIT,RECORD,BUILD branch;
    class TOOLS tool;
    class STOP guard;
    class EARLY_END,ANSWER terminal;
    style READY_PATH fill:transparent,stroke:#7EA3C1,stroke-width:1px,stroke-dasharray:5 5,color:#4E6A7E;
    linkStyle default stroke:#71869A,stroke-width:1.4px;
```

세부 노드나 함수 목록보다 실제 동작과 검증 경계를 확인하려면 다음 문서를 참고합니다.

| 주제 | 문서 |
| --- | --- |
| Finlife 상품 Tool과 멀티턴 조건 | [Agent 확장 명세](01-finlife-agent-expansion-spec.md) |
| 생성 모델과 Tool 호출 경계 | [생성 모델 전환](02-generation-model-backend-transition.md) |
| 구조화 출력과 Prompt 계약 | [Claude 구조화 출력](04-claude-structured-output-and-prompt-v3.md) |
| Agent 평가 범위 | [평가 데이터셋 계약](05-agent-evaluation-dataset-contract.md) |
