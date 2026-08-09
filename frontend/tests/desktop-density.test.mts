import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");

test("데스크톱에서는 전역 확대 대신 전용 밀도 규칙을 사용한다", () => {
  const desktopDensity = css.match(
    /@media \(min-width: 1001px\) \{([\s\S]*?)\n\}/,
  )?.[1];

  assert.ok(desktopDensity, "1001px 이상 데스크톱 밀도 규칙 필요");
  assert.match(desktopDensity, /--space-6:\s*29px/);
  assert.match(desktopDensity, /--evidence-width:\s*342px/);
  assert.doesNotMatch(desktopDensity, /\bzoom\s*:/);
  assert.doesNotMatch(desktopDensity, /transform:\s*scale\(0\.9\)/);
});

test("데스크톱의 주요 콘텐츠 폭과 글자 크기를 함께 낮춘다", () => {
  assert.match(css, /--desktop-content-max:\s*1404px/);
  assert.match(css, /--desktop-story-max:\s*1008px/);
  assert.match(css, /--desktop-hero-max:\s*1080px/);
  assert.match(css, /--desktop-hero-title-max:\s*49px/);
  assert.match(css, /--desktop-chat-title-max:\s*29px/);
});
