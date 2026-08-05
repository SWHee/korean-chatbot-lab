# Mascot Palette Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 얼굴 픽셀 손상을 제거하고 금융안심 UI에 맞는 쿨그레이·미스트 블루 캐릭터로 교체한다.

**Architecture:** 원본 레퍼런스의 형태와 인사 자세를 보존한 새 래스터 에셋을 만든다. 민트색 눈·입과 충돌하지 않는 마젠타 크로마키를 제거해 투명 PNG를 만들고 기존 Hero·프로필 참조만 새 버전으로 바꾼다.

**Tech Stack:** Built-in ImageGen, PNG alpha post-processing, Next.js Image

## Global Constraints

- 작업 범위는 `frontend-design-labs/`로 제한한다.
- 기존 `financial-guide-waving.png`는 보존한다.
- 몸통은 밝은 쿨그레이·미스트 블루, 귀·더듬이·말풍선은 저채도 블루로 구성한다.
- 얼굴 스크린은 딥 네이비, 눈·입은 깨끗한 민트색을 유지한다.
- 양팔 손목의 네이비 밴드를 모두 표현한다.
- 원본의 둥근 비율, 더듬이, 귀, 인사하는 손, 말풍선의 점 세 개를 유지한다.

---

### Task 1: 손상 원인 분리

**Files:**
- Inspect: `public/brand/financial-guide-waving.png`
- Inspect: ImageGen 크로마키 원본

- [ ] 초록 배경 생성본에서 눈·입이 깨끗한지 확인한다.
- [ ] 투명 처리본에서만 민트 픽셀이 손상되는지 확인한다.
- [ ] 마젠타 크로마키 사용을 단일 수정 가설로 고정한다.

### Task 2: 새 캐릭터 에셋 생성

**Files:**
- Create: `public/brand/financial-guide-waving-v2.png`

- [ ] 원본 레퍼런스를 입력으로 형태와 자세를 보존한 마젠타 배경 이미지를 생성한다.
- [ ] 몸통 `#DCE7F0` 계열, 귀·더듬이·말풍선 `#7FAED3` 계열, 네이비 손목 밴드 두 개를 명시한다.
- [ ] 마젠타 배경을 투명 처리한다.
- [ ] 전체 크기와 작은 프로필 크기에서 눈·입과 외곽선을 확인한다.

### Task 3: UI 적용과 검증

**Files:**
- Modify: `app/components/story/Hero.tsx`
- Modify: `app/components/BrandLogo.tsx`

- [ ] 두 컴포넌트의 이미지 경로를 새 에셋으로 변경한다.
- [ ] `npm test`와 `npm run build`를 실행한다.
- [ ] `http://localhost:3001/`에서 Hero와 프로필을 시각적으로 확인한다.
