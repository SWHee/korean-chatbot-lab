import assert from "node:assert/strict";
import test from "node:test";

import { getWorkspaceMode } from "../app/lib/workspace-mode.ts";

test("질문 전에는 상담 영역을 넓게 사용한다", () => {
  assert.equal(
    getWorkspaceMode({
      hasTurns: false,
      isStreaming: false,
      hasEvidence: false,
      hasError: false,
    }),
    "welcome",
  );
});

test("답변 생성 중에는 근거 확인 영역을 함께 연다", () => {
  assert.equal(
    getWorkspaceMode({
      hasTurns: true,
      isStreaming: true,
      hasEvidence: false,
      hasError: false,
    }),
    "searching",
  );
});

test("근거가 도착하면 같은 자리에 실제 근거를 표시한다", () => {
  assert.equal(
    getWorkspaceMode({
      hasTurns: true,
      isStreaming: false,
      hasEvidence: true,
      hasError: false,
    }),
    "evidence",
  );
});

test("근거 없는 답변이나 오류에서는 빈 패널을 남기지 않는다", () => {
  assert.equal(
    getWorkspaceMode({
      hasTurns: true,
      isStreaming: false,
      hasEvidence: false,
      hasError: true,
    }),
    "answer",
  );
});
