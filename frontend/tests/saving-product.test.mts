import assert from "node:assert/strict";
import test from "node:test";

import { productHeading } from "../app/lib/agent-stream.ts";
import type { Product } from "../app/lib/agent-stream.ts";

const savingProduct = {
  product_type: "saving",
  disclosure_month: "202607",
  company_code: "001",
  product_code: "SAVING-001",
  company_name: "테스트은행",
  product_name: "테스트적금",
  term_months: 12,
  base_interest_rate: 3.1,
  max_interest_rate: 3.5,
  reserve_type: "F",
  reserve_type_name: "자유적립식",
} as Product;

const depositProduct = {
  product_type: "deposit",
  disclosure_month: "202607",
  company_code: "001",
  product_code: "DEPOSIT-001",
  company_name: "테스트은행",
  product_name: "테스트예금",
  term_months: 12,
  base_interest_rate: 3.1,
  max_interest_rate: 3.5,
} as Product;

test("적금 후보에는 적금 제목을 사용한다", () => {
  assert.equal(productHeading([savingProduct]), "적금 후보");
});

test("정기예금 후보에는 기존 제목을 유지한다", () => {
  assert.equal(productHeading([depositProduct]), "정기예금 후보");
});
