/** Agent 답변 본문(Markdown)을 화면에 그릴 블록·인라인 조각으로 분해 */

export type Inline =
  | { kind: "text"; text: string }
  | { kind: "strong"; text: string }
  | { kind: "citation"; sourceId: string };

export type Block =
  | { kind: "heading"; level: 2 | 3; content: Inline[] }
  | { kind: "list"; ordered: boolean; items: Inline[][] }
  | { kind: "paragraph"; content: Inline[] };

const BULLET = /^[-*]\s+(.*)$/;
const NUMBERED = /^\d+\.\s+(.*)$/;
const HEADING = /^(#{2,3})\s+(.*)$/;
const INLINE = /\*\*(.+?)\*\*|\[(S\d+(?:\s*,\s*S\d+)*)\]/g;

/** **강조**와 [S1] 근거 표기를 인라인 조각으로 변환 */
export function parseInline(text: string): Inline[] {
  const parts: Inline[] = [];
  let cursor = 0;

  for (const match of text.matchAll(INLINE)) {
    const start = match.index ?? 0;
    if (start > cursor) parts.push({ kind: "text", text: text.slice(cursor, start) });

    if (match[1] !== undefined) {
      parts.push({ kind: "strong", text: match[1] });
    } else {
      for (const sourceId of match[2].split(",").map((id) => id.trim())) {
        parts.push({ kind: "citation", sourceId });
      }
    }
    cursor = start + match[0].length;
  }

  if (cursor < text.length) parts.push({ kind: "text", text: text.slice(cursor) });
  return parts;
}

/** 답변 전체를 제목·목록·문단 블록으로 분해 */
export function parseBlocks(answer: string): Block[] {
  const blocks: Block[] = [];
  let listItems: string[] = [];
  let listOrdered = false;
  let paragraphLines: string[] = [];

  const flushList = () => {
    if (listItems.length === 0) return;
    blocks.push({
      kind: "list",
      ordered: listOrdered,
      items: listItems.map(parseInline),
    });
    listItems = [];
  };

  const flushParagraph = () => {
    if (paragraphLines.length === 0) return;
    blocks.push({ kind: "paragraph", content: parseInline(paragraphLines.join("\n")) });
    paragraphLines = [];
  };

  for (const line of answer.split("\n")) {
    const heading = line.match(HEADING);
    const bullet = line.match(BULLET);
    const numbered = line.match(NUMBERED);

    if (heading) {
      flushList();
      flushParagraph();
      blocks.push({
        kind: "heading",
        level: heading[1].length === 2 ? 2 : 3,
        content: parseInline(heading[2]),
      });
      continue;
    }

    if (bullet || numbered) {
      flushParagraph();
      const ordered = Boolean(numbered);
      if (listItems.length > 0 && ordered !== listOrdered) flushList();
      listOrdered = ordered;
      listItems.push((bullet ?? numbered)![1]);
      continue;
    }

    if (!line.trim()) {
      flushList();
      flushParagraph();
      continue;
    }

    flushList();
    paragraphLines.push(line);
  }

  flushList();
  flushParagraph();
  return blocks;
}
