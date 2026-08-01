# LangFeather 연결 및 검증 기록

> 이 문서는 2026-07-28의 최초 연결 방식과 판단을 보존한 개발 기록이다. 현재
> LangFeather 0.2.0 설치·실행 방법은
> [개인 실행 안내](01-local-setup.md)를 따른다.

## 적용 목적과 선택

현재 프로젝트는 LangSmith의 24문항 평가와 별개로, LangGraph가 실제로 어떤 노드를
거쳤고 각 단계에서 무엇을 주고받았는지 빠르게 확인할 로컬 화면이 필요했다.

후보 연결 지점은 개별 `retrieve`·`generate` 노드와 compile된 최상위 그래프였다.
최상위 그래프를 한 번 감싸는 방식을 선택했다. 이 방식은 노드 구현을 바꾸지 않고
LangChain callback에 나타나는 내부 실행도 함께 수집하며, 앞으로 노드와 분기가
늘어나도 같은 연결 지점을 유지할 수 있기 때문이다.

## 적용 내용

검증 기준일은 2026-07-28이며, SDK는 다음 LangFeather commit으로 고정했다.

```text
a410f7c4211bbcabb9c9e5717bc23988797f9605
```

변경 범위는 다음과 같다.

| 파일 | 변경 |
| --- | --- |
| `pyproject.toml`, `uv.lock` | GitHub의 `sdk/python`과 `langchain` extra 고정 |
| `src/chatbot/main.py` | 환경 변수로 compile된 그래프 wrapper 선택, 종료 시 전송 마무리 |
| `.env.example` | 기본 비활성화 설정 예시 |
| `tests/conftest.py`, `tests/test_main.py` | 테스트의 추적 차단, 활성·비활성·종료 동작 검증 |

핵심 코드는 다음 흐름이다.

```python
if LANGFEATHER_ENABLED:
    langfeather.configure(endpoint=LANGFEATHER_ENDPOINT)
    rag_graph = langfeather.wrap_runnable(
        rag_graph,
        name="korean-chatbot-rag",
    )
```

실제 코드는 문자열 `"true"`일 때만 활성화한다. 기본값이 `false`이므로 기존 서버와
평가 스크립트는 LangFeather collector가 없어도 이전처럼 동작한다.

## 독립성 판단

이 연결은 LangSmith 설정을 덮어쓰거나 평가 코드를 호출하지 않는다. 두 추적 도구가
각자 callback을 추가할 수는 있지만, 이번 로컬 확인 명령에서는 LangSmith를 명시적으로
꺼 한 실행이 두 곳에 함께 기록되지 않게 한다.

LangFeather 전송은 크기가 제한된 메모리 queue의 백그라운드 작업이다. collector가
꺼져 있거나 전송에 실패해도 SDK는 경고를 남기고 원래 챗봇 반환값과 예외를
바꾸지 않는다. 대신 collector 장애 중인 trace의 영구 보관을 보장하지는 않는다.

## 확인한 호환성과 결과

LangFeather 원본 저장소의 SDK·통합 테스트 결과:

```text
163 passed
```

현재 프로젝트의 실제 두 노드 그래프로 사전 호환성을 확인한 결과:

- 일반 `invoke` 결과 동일
- streaming chunk 순서와 내용 동일
- 기존 callback 유지
- `retrieve`, `generate` 내부 실행 수집
- collector 연결 실패 시 원래 그래프 결과 유지

현재 프로젝트에 연결한 뒤 `tests/test_main.py`에서 확인한 항목:

- 비활성화 시 원래 compile graph 사용
- 활성화 시 endpoint 설정 후 최상위 graph를 한 번만 wrapper 처리
- 서버 종료 시 2초 제한으로 대기 중인 trace 전송
- 기존 일반 응답과 streaming endpoint 회귀 없음

전체 프로젝트 테스트 결과:

```text
66 passed
```

로컬 Docker collector의 health 응답과 실제 전송을 확인했다. 이어서 Streamlit
UI에서 법령 질문과 근거가 부족한 상품 질문을 실행했으며, 두 요청 모두 최상위
`LangGraph` 아래 `retrieve`, `generate` Node와 각 실행 시간을 로컬 화면에서
확인했다. LangFeather를 끈 일반 서버에서는 같은 요청이 기존 LangSmith에만
기록되는 것도 확인해 두 추적 설정이 독립적으로 동작함을 검증했다.

## 당시 확인하지 못한 정보

현재 `OllamaGenerator`는 LangChain의 chat model adapter가 아니라 Ollama HTTP API를
직접 호출한다. 그래서 LangGraph의 `retrieve`와 `generate` 노드 실행은 보이지만,
Ollama의 token 수, `done_reason`, model load 시간 같은 native 응답 지표가 자동으로
LLM observation에 채워지지는 않는다. 이 지표는 별도의 instrumentation 개선 단위다.

또한 당시 검증한 버전은 trace 확인과 수동 feedback 중심이었다. 현재 프로젝트의
Dataset 실행, evaluator 채점, 실험 간 평균 비교는 기존 LangSmith 평가 흐름에
남겨 둔다. Agent 평가 기능을 구현할 때 두 도구의 역할을 다시 비교한다.

## 다음 확장 조건

다음 항목은 실제 필요가 생길 때 각각 별도 작업으로 다룬다.

- FastAPI와 LangFeather를 하나의 Docker Compose network로 실행
- 요청별 `session_id` 또는 LangGraph `thread_id` 부여
- Ollama native 사용량과 종료 이유 추적
- 민감정보 redaction 또는 payload 보존 정책
- LangSmith 평가와 LangFeather 로컬 trace의 같은 실행 비교
