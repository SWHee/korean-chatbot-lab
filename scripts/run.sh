#!/usr/bin/env bash

# Next.js와 FastAPI 로컬 개발 서버 동시 실행
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PID=""
WEB_PID=""

cleanup() {
    trap - EXIT INT TERM

    if [[ -n "$API_PID" ]]; then
        kill "$API_PID" 2>/dev/null || true
    fi
    if [[ -n "$WEB_PID" ]]; then
        kill "$WEB_PID" 2>/dev/null || true
    fi

    wait "$API_PID" "$WEB_PID" 2>/dev/null || true
}

if ! command -v uv >/dev/null; then
    echo "uv를 찾지 못했습니다. https://docs.astral.sh/uv/ 에서 설치해 주세요."
    exit 1
fi

if ! command -v npm >/dev/null; then
    echo "npm을 찾지 못했습니다. Node.js를 설치해 주세요."
    exit 1
fi

if [[ ! -x "$PROJECT_ROOT/frontend/node_modules/.bin/next" ]]; then
    echo "frontend 의존성이 없습니다. 먼저 'cd frontend && npm ci'를 실행해 주세요."
    exit 1
fi

cd "$PROJECT_ROOT"
trap cleanup EXIT INT TERM

echo "FastAPI: http://127.0.0.1:8000/docs"
echo "Next.js: http://localhost:3001"
echo "종료: Ctrl+C"

uv run fastapi dev &
API_PID=$!

(
    cd frontend
    npm run dev
) &
WEB_PID=$!

wait "$API_PID" "$WEB_PID"
