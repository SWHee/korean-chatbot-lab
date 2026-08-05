import assert from "node:assert/strict";
import test from "node:test";

import { storyPhaseAt, storyPhaseProgress } from "../app/lib/story-state.ts";

test("storyPhaseAt divides the scroll journey into problem, search, and evidence", () => {
  assert.equal(storyPhaseAt(0), 0);
  assert.equal(storyPhaseAt(0.35), 0);
  assert.equal(storyPhaseAt(0.36), 1);
  assert.equal(storyPhaseAt(0.69), 1);
  assert.equal(storyPhaseAt(0.7), 2);
  assert.equal(storyPhaseAt(1), 2);
});

test("storyPhaseProgress clamps each phase to its local progress range", () => {
  assert.ok(Math.abs(storyPhaseProgress(0.18, 0) - 0.5) < 0.0001);
  assert.ok(Math.abs(storyPhaseProgress(0.53, 1) - 0.5) < 0.0001);
  assert.equal(storyPhaseProgress(0.8, 1), 1);
  assert.equal(storyPhaseProgress(0.5, 2), 0);
  assert.equal(storyPhaseProgress(1, 2), 1);
});
