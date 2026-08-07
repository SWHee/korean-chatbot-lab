import assert from "node:assert/strict";
import test from "node:test";

import { createThreadId } from "../app/lib/thread-id.ts";

test("randomUUID를 쓸 수 없는 HTTP 환경에서도 대화 ID를 만든다", () => {
  const threadId = createThreadId({});

  assert.match(threadId, /^thread-\d+-[a-z0-9]+$/);
});
