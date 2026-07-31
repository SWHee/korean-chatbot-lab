# Agent 확장 전 생성 모델 backend 전환 계획

- 작성일: 2026-08-01
- 상태: 설계 완료, Anthropic API 연결 전
- 범위: 법령 RAG 생성과 이후 LangGraph Agent model

## 전환을 결정한 이유

프로젝트는 처음부터 생성 모델을 바꾸지 않고 로컬 Qwen3를 사용해 왔다. 이 과정에서
Hugging Face 직접 추론, Ollama 모델 서버, 양자화 모델, Structured Output과
스트리밍을 경험했다. 반면 4B 로컬 모델의 한국어 답변 품질과 생성 속도를 보완하는 데
시간이 많이 들면서, Tool Calling·라우팅·멀티턴·평가 같은 Agent 개발에 사용할 시간이
줄어들었다.

Finlife client는 정기예금 호출·정규화·조건 비교와 적금 endpoint 계약까지 확인했다.
아직 Graph에 Product Node를 연결하기 전이므로, 지금 생성 모델만 바꾸면 기존 법령
RAG를 고정된 비교 기준으로 사용할 수 있다. Agent Graph와 모델을 동시에 바꿔 결과의
원인을 구분하기 어려워지는 상황도 피할 수 있다.

이번 전환은 오픈웨이트 실습을 포기하는 결정이 아니다. 서비스 개발 경로에서는 관리형
API로 Agent 구현 속도를 확보하고, 모델 엔지니어링은 별도의 LoRA·vLLM 실습으로
분리하는 결정이다.

## 모델별 역할

| backend | 역할 | 운영 방식 |
| --- | --- | --- |
| Anthropic Claude Haiku | 첫 API 개발 모델 | 남은 크레딧으로 RAG·Structured Output·Tool Calling 검증 |
| OpenAI API | 후속 개발 모델 | 같은 계약으로 설정만 바꿔 연결 |
| Ollama Qwen3 | 로컬 기준선과 오픈웨이트 실습 | 코드를 보존하고 필요할 때 명시적으로 선택 |
| Hugging Face Qwen 생성기 | 제거 대상 | 현행 구조화 RAG와 호환되지 않는 과거 직접 추론 구현 |

Ollama는 당장 자동 fallback으로 사용하지 않는다. `CHATBOT_BACKEND`로 사람이 선택할
수 있는 로컬 backend로 남긴다. 스트리밍 중간 실패나 Tool 실행 이후 자동 전환은
답변 중복과 Tool 재실행 정책이 필요하므로, 실제 배포 안정성 요구가 생긴 뒤 별도로
설계한다.

Hugging Face 생성기를 제거해도 KURE-v1 임베딩은 유지한다. 검색용 KURE-v1은
`sentence-transformers`와 PyTorch를 계속 사용하므로 Hugging Face 생태계 전체를
제거한다는 의미는 아니다.

## backend 전환 경계

현재 RAG가 사용하는 생성 계약은 다음 네 기능이다.

```text
generate
stream
generate_structured
stream_structured
```

각 공급자 구현이 이 계약을 만족하게 하고, 애플리케이션은 환경 변수로 구현체만
선택한다.

```text
CHATBOT_BACKEND=anthropic → Anthropic 생성기
CHATBOT_BACKEND=openai    → OpenAI 생성기
CHATBOT_BACKEND=ollama    → 기존 Ollama 생성기
```

공급자 API 응답을 Graph State나 Node 전체로 퍼뜨리지 않는다. 법령 검색, Finlife
client, Pydantic 응답 모델과 FastAPI endpoint는 그대로 두고 생성 경계에서 메시지,
구조화 결과, 스트림 조각을 프로젝트 형식으로 바꾼다.

Tool-calling Agent 단계에서는 같은 공급자 설정으로 LangChain ChatModel의
`bind_tools()`를 사용한다. RAG 연결을 위해 만든 공급자 설정과 Agent 설정이 서로 다른
모델 이름이나 API key를 읽지 않도록 한 곳에서 관리한다.

## 작은 단위의 전환 순서

1. Claude Haiku 일반 호출과 Structured Output 각 1건 확인
2. Anthropic 생성기를 현재 법령 RAG에 연결
3. 비스트리밍·스트리밍 대표 질문을 UI에서 확인
4. 기존 24문항으로 Ollama 기준선과 생성 모델만 비교
5. `CHATBOT_BACKEND=anthropic`을 개발 기본값으로 전환
6. HF 생성기와 `hf` backend 선택지 제거
7. Product Node POC 재개
8. Anthropic 검증 후 OpenAI 구현을 같은 계약으로 추가

기존 24문항은 Agent 전체 평가 데이터로 사용하지 않는다. 다만 corpus, KURE-v1,
Chroma, 검색 설정과 prompt를 고정하고 생성 모델 하나만 비교하는 회귀 평가에는 계속
사용한다.

## Docker·CI/CD 후속 대응

생성 모델을 API로 바꿔도 API와 web 이미지를 새로 나눌 필요는 없다. 같은 API 이미지
안에 공급자 client를 포함하고 실행 환경 변수로 backend를 선택한다.

| 대상 | 전환 후 변경 |
| --- | --- |
| API 이미지 | Anthropic·OpenAI client 의존성 포함, HF 생성 전용 의존성 제거 검토 |
| Compose `api` | backend·모델 이름·API key를 런타임 환경 변수로 전달 |
| Compose `ollama` | 기본 의존성에서 분리하고 로컬 실행용 profile로 보존 검토 |
| CI build | 현재처럼 API·web 이미지 빌드, API key를 build argument로 넣지 않음 |
| EC2 | 서버의 비공개 환경 변수 또는 GitHub Secret으로 key 전달 |

현재 Compose는 `api`가 `ollama`의 healthcheck를 기다리도록 고정되어 있다. API backend가
기본이 되면 이 의존성을 제거해야 Ollama를 띄우지 않고도 서비스가 시작된다. Ollama를
사용할 때만 다음과 같이 명시적으로 실행할 수 있는 구성을 후속 배포 작업에서 검토한다.

```bash
CHATBOT_BACKEND=ollama docker compose --profile ollama up
```

Anthropic에서 OpenAI로 바꿀 때는 이미지를 공급자별로 다시 만들지 않는다. 두 client가
포함된 같은 이미지를 사용하고 `CHATBOT_BACKEND`, 모델 이름, API key를 바꾼 뒤
container만 재시작하는 것을 목표로 한다.

Docker Hub·EC2·GitHub Actions의 구체적인 변경과 검증 결과는
[`Docker·EC2·CI/CD 챌린지`](../08-ci-cd-pipeline/README.md)에 기록한다. 이 문서에는
Agent 개발에서 모델 backend를 바꾼 이유와 경계만 유지한다.

## 로컬 API key 준비

연결 코드를 작성하기 전까지 key는 사용되지 않으므로 미리 넣을 필요는 없다. 첫 API
smoke test 직전에 Git에서 제외된 루트 `.env`에 다음 값을 추가한다.

```dotenv
CHATBOT_BACKEND=anthropic
ANTHROPIC_API_KEY=sk-ant-실제키
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

- 따옴표는 필수가 아니며 key 앞뒤에 공백을 넣지 않음
- `.env.example`에는 실제 key가 아닌 변수 이름과 placeholder만 기록
- key를 코드, Dockerfile, Compose 원문, trace metadata에 기록하지 않음
- 터미널에 같은 변수가 이미 설정되어 있으면 현재 `load_dotenv(override=False)` 특성상
  터미널 값이 `.env`보다 우선
- key가 노출되면 Git에서 파일만 지우지 말고 공급자 Console에서 즉시 폐기·재발급

OpenAI 연결 단계에서는 같은 방식으로 다음 값을 추가한다.

```dotenv
CHATBOT_BACKEND=openai
OPENAI_API_KEY=실제키
OPENAI_MODEL=전환 시점에 선택한 모델
```

Docker Compose와 EC2에는 로컬 `.env` 파일을 이미지에 복사하지 않는다. 실제 배포를
시작할 때 runtime secret 전달 방식을 별도로 검증한다.

## 완료 기준

- Claude의 일반·구조화·스트리밍 응답 확인
- 기존 RAG Pydantic 검증과 근거 렌더링 유지
- Ollama와 같은 질문의 품질·첫 응답·전체 시간·비용 비교
- Ollama를 명시적으로 다시 선택할 수 있음
- HF 생성 경로 제거 후 전체 테스트 통과
- API key가 Git diff, 이미지와 trace에 포함되지 않음

## 공식 참고

- [Claude 모델 목록](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Claude Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Claude Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [LangChain ChatAnthropic](https://docs.langchain.com/oss/python/integrations/chat/anthropic)
- [LangChain ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai)
