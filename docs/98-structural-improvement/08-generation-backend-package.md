---
date: 2026-08-09
status: completed
result: Anthropic·Ollama 생성기를 한 경계로 모으고 사용하지 않는 HF 생성 코드 제거
---

# 생성 backend 패키지 정리

## 문제

Anthropic, Ollama, Hugging Face 생성기가 `chatbot` 루트에 나란히 있었고 생성기 선택 코드도
별도 파일로 떨어져 있었다. 현재 사용하지 않는 HF Qwen 생성기는 모델을 애플리케이션에 직접
적재하므로 Ollama와 역할이 겹쳤다.

## 판단

Anthropic을 기본 생성기로, Ollama를 로컬 오픈웨이트 실험과 수동 대체 생성기로 유지했다.
HF 생성 코드는 제거하되 KURE 임베딩에 필요한 `torch`, `transformers` 의존성은 보존했다.

`factory.py`는 `CHATBOT_BACKEND` 설정에 맞는 생성기를 만드는 단일 진입점이다. 자동 폴백은
아니며, 모델이 조용히 바뀌어 답변 품질이 달라지는 상황을 피하기 위해 이번 범위에는 넣지 않았다.

## 적용

- `generation/anthropic.py`, `generation/ollama.py`로 생성기 구현 이동
- `generation/factory.py`로 생성기 선택 책임 이동
- HF 생성기와 `CHATBOT_BACKEND=hf` 분기 제거
- HF 생성기에만 필요했던 `accelerate` 직접 의존성 제거

## 결과

호출부는 `chatbot.generation.create_generator`만 사용한다. 기본 Anthropic과
`CHATBOT_BACKEND=ollama` 수동 전환 동작은 유지된다.

검증: 생성기·API 수명주기·Agent 모델 테스트
