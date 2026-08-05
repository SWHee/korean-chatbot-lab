# Hero, Scroll, and Background Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 오른쪽 로봇 히어로, 느긋한 스크롤 장면, 깊이 있는 단일 네이비 배경을 구현한다.

**Architecture:** 기존 `Hero`와 `Problem` 컴포넌트 및 CSS 토큰을 확장한다. 스크롤 입력은
가로채지 않고 섹션 높이와 검증 가능한 단계 계산만 조정하며, 하나의 로봇 PNG를 히어로와
`BrandLogo`가 공유한다.

**Tech Stack:** Next.js 16, React 19, TypeScript, CSS, Node test runner

## Global Constraints

- 작업 범위는 `frontend-design-labs/`로 제한
- 백엔드와 채팅 데이터 계약 변경 금지
- 새 패키지 추가 금지
- 모바일 및 모션 최소화 환경에서 일반 세로 흐름 보존

---

### Task 1: 스크롤 단계 체감 조정

**Files:**
- Modify: `tests/story-state.test.mts`
- Modify: `app/lib/story-state.ts`
- Modify: `app/components/story/Problem.tsx`
- Modify: `app/globals.css`

- [ ] 단계 체류 구간을 검증하는 실패 테스트 작성 및 실패 확인
- [ ] 테스트를 만족하는 단계 경계 구현
- [ ] 스토리 높이와 장면 전환 거리 조정
- [ ] 테스트 재실행

### Task 2: 로봇 자산과 히어로 적용

**Files:**
- Create: `public/brand/financial-guide.png`
- Modify: `app/components/story/Hero.tsx`
- Modify: `app/components/BrandLogo.tsx`
- Modify: `app/globals.css`

- [ ] 레퍼런스 기반 투명 로봇 자산 생성 및 가장자리 검증
- [ ] 히어로 2열과 반응형 배치 구현
- [ ] 동일 자산을 헤더와 답변 프로필에 적용

### Task 3: 단일 네이비 배경 깊이 보완

**Files:**
- Modify: `app/globals.css`

- [ ] 고정된 방사형 조명과 저대비 패턴 추가
- [ ] 섹션 배경 투명성과 텍스트 대비 유지
- [ ] 모션 최소화 환경에서 장식 정지 확인

### Task 4: 검증

**Files:**
- Verify only

- [ ] `npm test` 실행
- [ ] `npm run build` 실행
- [ ] 1280px, 768px, 375px와 reduced-motion에서 브라우저 확인
- [ ] 히어로부터 상담까지 스크롤하고 입력 포커스·오류 상태 확인
