# Finbom Brand and Disclaimer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 현재 공개 UI와 README의 서비스명을 핀봄으로 통일하고, 답변의 법적·금융적 한계를 명확히 안내한다.

**Architecture:** 사용자에게 노출되는 현재 UI와 공개 문서만 변경한다. 과거 설계 기록, backend 계약, 원격 저장소 이름과 Git remote는 유지한다.

**Tech Stack:** Next.js, React, Markdown, built-in ImageGen

## Global Constraints

- 서비스명은 `핀봄`, 영문명은 `Finbom`, 마스코트명은 `포키(Poki)`로 구분한다.
- 고지는 법령 자체가 아니라 서비스의 답변과 표시 정보에 법적 효력이 없음을 설명한다.
- backend와 스트리밍 계약은 변경하지 않는다.
- 원격 저장소 이름과 Git remote는 변경하지 않는다.

---

### Task 1: 사용자-facing 명칭과 고지 교체

**Files:**
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `frontend-design-labs/app/layout.tsx`
- Modify: `frontend-design-labs/app/components/story/Hero.tsx`
- Modify: `frontend-design-labs/app/components/story/Problem.tsx`
- Modify: `frontend-design-labs/app/components/ChatConsole.tsx`
- Modify: `frontend-design-labs/app/components/Conversation.tsx`

- [x] 현재 UI의 `금융안심`을 `핀봄`으로 교체한다.
- [x] README의 서비스명과 소개를 `핀봄 / Finbom` 기준으로 교체한다.
- [x] 상담 하단과 README에 동일한 의미의 참고용·비자문 고지를 반영한다.
- [x] `rg`로 사용자-facing 이전 명칭과 고지 중복을 확인한다.

### Task 2: README 히어로 교체

**Files:**
- Create: `docs/assets/readme-hero-finbom.png`
- Modify: `README.md`

- [x] 포키의 형태와 색을 유지한 가로 배너를 built-in ImageGen으로 생성한다.
- [x] 법령 문서·상품 정보·근거 연결 경로로 현재보다 높은 정보 밀도를 만든다.
- [x] 텍스트 생성 오류를 피하기 위해 이미지 안에 서비스명이나 문장을 넣지 않는다.
- [x] 새 파일을 프로젝트에 저장하고 README 경로를 교체한다.

### Task 3: 검증

**Files:**
- Test: `frontend-design-labs/`
- Verify: `README.md`, `docs/assets/readme-hero-finbom.png`

- [x] `npm run build`로 Next.js production build를 확인한다.
- [x] 새 이미지의 크기·형식과 README 내부 링크를 확인한다.
- [x] 변경 대상의 diff와 기존 사용자 변경을 분리해 확인한다.
