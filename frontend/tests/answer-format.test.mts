import assert from "node:assert/strict";
import test from "node:test";

import { parseBlocks } from "../app/lib/answer-format.ts";

test("완성된 Markdown 표를 정렬 정보와 함께 표 블록으로 변환한다", () => {
  const blocks = parseBlocks(`| 순위 | 은행명 | 기본금리 |
| :---: | :--- | ---: |
| 1위 | 전북은행 | **3.76%** |
| 2위 | 케이뱅크 | 3.71% |`);

  assert.deepEqual(blocks, [
    {
      kind: "table",
      header: [
        [{ kind: "text", text: "순위" }],
        [{ kind: "text", text: "은행명" }],
        [{ kind: "text", text: "기본금리" }],
      ],
      alignments: ["center", "left", "right"],
      rows: [
        [
          [{ kind: "text", text: "1위" }],
          [{ kind: "text", text: "전북은행" }],
          [{ kind: "strong", text: "3.76%" }],
        ],
        [
          [{ kind: "text", text: "2위" }],
          [{ kind: "text", text: "케이뱅크" }],
          [{ kind: "text", text: "3.71%" }],
        ],
      ],
    },
  ]);
});

test("열이 부족한 데이터 행은 빈 셀로 보정한다", () => {
  const blocks = parseBlocks(`| 은행명 | 상품명 | 금리 |
| --- | --- | --- |
| 전북은행 | 정기예금 |`);

  assert.deepEqual(blocks, [
    {
      kind: "table",
      header: [
        [{ kind: "text", text: "은행명" }],
        [{ kind: "text", text: "상품명" }],
        [{ kind: "text", text: "금리" }],
      ],
      alignments: [null, null, null],
      rows: [
        [
          [{ kind: "text", text: "전북은행" }],
          [{ kind: "text", text: "정기예금" }],
          [],
        ],
      ],
    },
  ]);
});

test("구분선이 아직 없는 스트리밍 표는 일반 문단으로 유지한다", () => {
  const blocks = parseBlocks("| 순위 | 은행명 | 기본금리 |");

  assert.deepEqual(blocks, [
    {
      kind: "paragraph",
      content: [{ kind: "text", text: "| 순위 | 은행명 | 기본금리 |" }],
    },
  ]);
});
