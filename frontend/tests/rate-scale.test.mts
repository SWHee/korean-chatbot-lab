import assert from "node:assert/strict";
import test from "node:test";

import { createRateScale, ratePosition } from "../app/lib/rate-scale.ts";

test("후보 금리를 같은 0.5%p 구간에 배치한다", () => {
  const scale = createRateScale([3.76, 3.76, 3.71, 3.71, 3.65, 3.85]);

  assert.deepEqual(scale, { min: 3.5, max: 4 });
  assert.equal(ratePosition(3.65, scale), 30);
  assert.equal(ratePosition(3.85, scale), 70);
});

test("표시할 금리가 없으면 비교 구간을 만들지 않는다", () => {
  assert.equal(createRateScale([null, null]), null);
});
