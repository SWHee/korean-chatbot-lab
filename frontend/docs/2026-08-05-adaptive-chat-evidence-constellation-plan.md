# Adaptive Chat and Evidence Constellation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 상담 상태에 맞는 작업면과 스크롤에 연결된 근거 연결망, 인사하는 금융안심 캐릭터를 구현한다.

**Architecture:** `workspaceMode()`를 순수 함수로 분리해 레이아웃 상태를 검증한다. 페이지에
고정된 `EvidenceConstellation` SVG를 한 번만 렌더링하고 기존 스크롤 진행도를 CSS 변수로
전달한다. 캐릭터는 새 투명 PNG 하나를 Hero와 `BrandLogo`가 공유한다.

**Tech Stack:** Next.js 16, React 19, TypeScript, CSS, SVG, Node test runner

## Global Constraints

- 작업 범위는 `frontend-design-labs/`로 제한한다.
- 채팅 API, 스트림 이벤트와 다중 턴 계약을 변경하지 않는다.
- 배경색 `#0B1220`을 바꾸거나 섹션별 색상 페이드를 넣지 않는다.
- 새 패키지와 WebGL을 추가하지 않는다.
- 1000px 이하와 모션 최소화 환경에서는 단순하고 읽을 수 있는 흐름을 유지한다.

---

### Task 1: 상담 레이아웃 상태

**Files:**
- Create: `app/lib/workspace-mode.ts`
- Create: `tests/workspace-mode.test.mts`
- Modify: `app/components/ChatConsole.tsx`
- Create: `app/components/EvidencePending.tsx`
- Modify: `app/globals.css`

**Interfaces:**
- `workspaceMode({ hasTurns, isStreaming, hasEvidence, hasError }): "welcome" | "searching" | "evidence" | "answer"`
- `EvidencePending({ message: string })`

- [ ] 상태별 기대값 네 가지를 검증하는 테스트를 먼저 작성하고 `npm test` 실패를 확인한다.
- [ ] `workspaceMode()`를 최소 구현해 테스트를 통과시킨다.
- [ ] `ChatConsole`의 `data-workspace-mode`와 검색 중 패널을 연결한다.
- [ ] CSS에서 `welcome`·`answer`는 한 열, `searching`·`evidence`는 두 열로 표시한다.

### Task 2: Evidence Constellation

**Files:**
- Create: `app/components/story/EvidenceConstellation.tsx`
- Modify: `app/page.tsx`
- Modify: `app/globals.css`

**Interfaces:**
- `EvidenceConstellation({ target: RefObject<HTMLElement | null> })`

- [ ] 점 12개, 경로 7개, 문서 윤곽 3개를 가진 장식용 SVG를 작성한다.
- [ ] 기존 `useScrollProgress()` 값으로 `--constellation-progress`를 전달한다.
- [ ] 스크롤에 따라 흩어짐·연결·수렴 상태를 CSS transform과 stroke 속성으로 표현한다.
- [ ] Chat, 모바일과 모션 최소화 환경에서 움직임과 대비를 낮춘다.

### Task 3: 인사 캐릭터

**Files:**
- Create: `public/brand/financial-guide-waving.png`
- Modify: `app/components/story/Hero.tsx`
- Modify: `app/components/BrandLogo.tsx`

**Interfaces:**
- `/brand/financial-guide-waving.png`를 Hero와 프로필에서 공유한다.

- [ ] 레퍼런스의 둥근 인사 자세와 말풍선 배지를 유지한 크로마키 이미지를 생성한다.
- [ ] 크로마키를 제거하고 알파 채널과 가장자리 잔상을 확인한다.
- [ ] 새 경로로 Hero와 프로필 이미지를 교체한다.

### Task 4: 검증

**Files:**
- Verify only

- [ ] `npm test`와 `npm run build`를 실행한다.
- [ ] 1280px, 768px, 375px에서 가로 넘침과 레이아웃 상태를 확인한다.
- [ ] 실제 질문 한 건으로 검색 중 패널, 근거 교체, 자동 스크롤과 입력 복귀를 확인한다.
- [ ] 브라우저 콘솔 오류와 경고를 확인한다.
