# Agent POC CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude 기반 멀티턴 Agent를 web·api 두 컨테이너로 실행하고 EC2까지 자동 배포한다.

**Architecture:** Next.js만 `3000` 포트로 공개하고 FastAPI는 Compose 내부에서 연결한다. Claude와 Finlife는 외부 API를 사용하며 Chroma, KURE cache, SQLite 대화 상태는 컨테이너 밖에 보존한다.

**Tech Stack:** Docker, Docker Compose, FastAPI, Next.js, GitHub Actions, Docker Hub, AWS EC2

## Global Constraints

- Ollama service와 자동 fallback은 배포 범위에서 제외
- 실제 API key는 Git·Docker 이미지·workflow 원문에 저장하지 않음
- 기존 사용자 변경사항은 수정하거나 되돌리지 않음
- 외부 공개 포트는 Next.js `3000`만 사용

---

### Task 1: API 이미지와 build context 정리

**Files:**
- Modify: `.dockerignore`
- Modify: `Dockerfile`
- Create: `frontend/.dockerignore`
- Create: `frontend/Dockerfile`
- Modify: `frontend/next.config.ts`

- [x] **Step 1:** 현재 `.runtime`이 build context에 포함되는 검사를 실패로 확인
- [x] **Step 2:** `.runtime`, SQLite, 로컬 산출물을 `.dockerignore`에 추가
- [x] **Step 3:** 의존성 layer와 프로젝트 source layer를 나누어 Docker cache 재사용
- [x] **Step 4:** 현재 Next.js `3001` 포트용 standalone production 이미지 작성
- [x] **Step 5:** `docker build`로 API·web 이미지 생성 확인

### Task 2: Agent 기준 Compose 작성

**Files:**
- Modify: `docker-compose.yml`

- [x] **Step 1:** 현재 Compose에 `ollama` service가 남아 있는 검사 확인
- [x] **Step 2:** `web`, `api`만 남기고 Anthropic·Finlife 환경 변수 전달
- [x] **Step 3:** Chroma, KURE cache, SQLite runtime volume 연결
- [x] **Step 4:** placeholder key로 `docker compose config` 결과 검증

### Task 3: GitHub Actions 배포 갱신

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [x] **Step 1:** Python·Next.js 검사를 실행하는 CI 유지
- [x] **Step 2:** api·web 이미지를 `latest`와 commit SHA 두 tag로 발행
- [x] **Step 3:** EC2의 기존 `.env`와 index를 검사하고 정확한 SHA 이미지로 재시작
- [x] **Step 4:** Compose health와 로컬 `3000` HTTP 응답 확인 추가

### Task 4: 실행 문서 갱신

**Files:**
- Modify: `docs/08-ci-cd-pipeline/README.md`
- Modify: `docs/08-ci-cd-pipeline/01-challenge-workflow.md`
- Modify: `docs/08-ci-cd-pipeline/03-model-backend-options.md`
- Create: `docs/08-ci-cd-pipeline/02-devlog/02-agent-deployment-runtime.md`

- [x] **Step 1:** 현재 두-service 구조와 진행 위치를 README에 반영
- [x] **Step 2:** 로컬 준비·EC2 최초 준비·자동 배포 순서를 쉬운 명령으로 정리
- [x] **Step 3:** 파일별 Docker·Compose 문법을 짧게 설명
- [x] **Step 4:** 실제 검증 결과와 남은 수동 배포 작업만 DEVLOG에 기록

### Task 5: 전체 검증

**Files:**
- Verify only

- [x] **Step 1:** `docker compose config`에서 service·image·volume 확인
- [x] **Step 2:** `.venv/bin/pytest -q` 실행
- [x] **Step 3:** `npm run build` 실행
- [x] **Step 4:** API·web Docker 이미지 build 및 image history 확인
- [x] **Step 5:** `git diff --check`와 관련 파일 diff 검토
