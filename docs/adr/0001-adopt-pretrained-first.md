# ADR 0001. 주력 챗봇은 사전학습 모델로 시작한다

- 상태: Accepted
- 날짜: 2026-06-30
- 구현 상태: Not started

## 배경

이 프로젝트는 처음에 작은 한국어 Transformer를 직접 구현하며 언어 모델의
내부 흐름을 학습했다. 토크나이저, 다음 토큰 데이터셋, 작은 Transformer,
Step 04의 `calculate_loss()`까지 진행했지만 전체 학습과 생성 품질을 확보하려면
상당한 데이터와 시간이 더 필요하다.

현재 우선 학습 목표는 모델 아키텍처 자체보다 FastAPI 서빙, LangChain/RAG,
LangSmith 평가, LangGraph 상태 흐름을 직접 구현하고 설명하는 것이다.

## 문제

작은 from-scratch 모델은 검색된 문맥을 이해하고, 질문과 관련된 정보를 고르고,
지시를 따르며 자연스러운 답변을 만드는 능력이 제한적이다. RAG가 관련 문서를
찾아주더라도 생성 모델의 기본 능력을 대신 만들어주지는 않는다.

반대로 LangChain 타입이나 특정 외부 API를 프로젝트 전체에서 직접 사용하면
나중에 모델을 비교하거나 교체할 때 애플리케이션 코드까지 함께 바뀔 수 있다.

## 고려한 선택지

1. From-scratch 모델의 학습과 생성을 먼저 완성한다.
2. LangChain의 모델 인터페이스를 프로젝트의 핵심 경계로 사용한다.
3. 로컬 사전학습 모델로 시작하되 프로젝트가 소유하는 작은 생성 경계를 둔다.

## 결정

주력 트랙은 로컬 Hugging Face instruction-tuned 모델로 시작한다. 애플리케이션
코드가 입력 prompt를 받아 생성된 text를 반환하는 최소 `Generator` 경계에
의존하도록 설계한다.

첫 구현에서는 Hugging Face backend 하나만 만든다. 외부 API나 from-scratch
모델은 실제 비교 필요가 생길 때 adapter로 추가한다. LangChain 연결도 생성과
FastAPI 흐름이 동작한 뒤 별도 단계에서 구현한다.

정확한 Hugging Face 모델은 이 ADR에서 결정하지 않는다. 한국어 instruction
품질, 모델 크기, 메모리, 라이선스, chat template, PyTorch/MPS 호환성, Colab
실행 가능성을 비교한 뒤 별도 결정으로 남긴다.

## 결정 이유

- 현재 목표인 RAG와 agent 애플리케이션 학습으로 빠르게 이동할 수 있다.
- 토크나이저, tensor, `generate()`와 device 처리를 계속 PyTorch 관점에서 볼 수
  있다.
- 모델별 SDK나 LangChain 타입이 FastAPI와 핵심 애플리케이션 경계로 퍼지는 것을
  막을 수 있다.
- 이후 같은 입력으로 Hugging Face, 외부 API, from-scratch 결과를 비교할 수 있다.
- 필요한 구현체만 추가하므로 교체 가능성을 이유로 과도한 추상화를 만들지 않는다.

## 감수하는 단점

- 모델 선택과 로컬 실행에 메모리 및 성능 제약이 있다.
- 작은 생성 경계와 framework adapter를 직접 유지해야 한다.
- 사전학습 모델 내부를 처음부터 구현하는 경험은 주력 트랙에서 더 진행하지 않는다.
- 파인튜닝을 즉시 다루지 않으므로 말투나 지시 수행 개선은 이후 단계로 미룬다.

## 결과와 다음 단계

기존 코드는 `experiments/from_scratch/`에 일시 중단된 학습 실험으로 보존한다.
다음 작업에서는 챗봇 용도와 평가 질문을 정하고, 로컬 Mac과 Colab 환경에서
실행할 Hugging Face 모델 후보를 비교한다.

분기, 재시도 또는 상태 관리가 실제로 필요해질 때 LangGraph를 도입하고, RAG와
prompt만으로 해결되지 않는 말투나 행동 문제가 확인될 때 파인튜닝을 검토한다.
