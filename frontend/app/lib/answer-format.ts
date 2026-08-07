/** Agent 답변 본문(Markdown)을 화면에 그릴 블록·인라인 조각으로 분해 */

export type Inline =
  | { kind: "text"; text: string }
  | { kind: "strong"; text: string }
  | { kind: "citation"; sourceId: string };

export type TableAlignment = "left" | "center" | "right" | null;

export type Block =
  | { kind: "heading"; level: 2 | 3; content: Inline[] }
  | { kind: "list"; ordered: boolean; items: Inline[][] }
  | {
      kind: "table";
      header: Inline[][];
      alignments: TableAlignment[];
      rows: Inline[][][];
    }
  | { kind: "paragraph"; content: Inline[] };

const BULLET = /^[-*]\s+(.*)$/;
const NUMBERED = /^\d+\.\s+(.*)$/;
const HEADING = /^(#{2,3})\s+(.*)$/;
const INLINE = /\*\*(.+?)\*\*|\[(S\d+(?:\s*,\s*S\d+)*)\]/g;
const TABLE_DIVIDER = /^:?-{3,}:?$/;

/** 앞뒤 파이프와 이스케이프된 파이프를 고려한 표 셀 분리 */
function splitTableRow(line: string): string[] | null {
  const trimmed = line.trim();
  if (!trimmed.includes("|")) return null;

  const content = trimmed.replace(/^\|/, "").replace(/\|$/, "");
  const cells: string[] = [];
  let cell = "";

  for (let index = 0; index < content.length; index += 1) {
    const character = content[index];
    if (character === "\\" && content[index + 1] === "|") {
      cell += "|";
      index += 1;
      continue;
    }
    if (character === "|") {
      cells.push(cell.trim());
      cell = "";
      continue;
    }
    cell += character;
  }

  cells.push(cell.trim());
  return cells;
}

function tableAlignments(line: string, columnCount: number): TableAlignment[] | null {
  const cells = splitTableRow(line);
  if (!cells || cells.length !== columnCount || !cells.every((cell) => TABLE_DIVIDER.test(cell))) {
    return null;
  }

  return cells.map((cell) => {
    if (cell.startsWith(":") && cell.endsWith(":")) return "center";
    if (cell.endsWith(":")) return "right";
    if (cell.startsWith(":")) return "left";
    return null;
  });
}

function tableCells(cells: string[], columnCount: number): Inline[][] {
  return Array.from({ length: columnCount }, (_, index) => parseInline(cells[index] ?? ""));
}

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
  const lines = answer.split("\n");

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

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const headerCells = splitTableRow(line);
    const alignments = headerCells
      ? tableAlignments(lines[index + 1] ?? "", headerCells.length)
      : null;

    if (headerCells && alignments) {
      flushList();
      flushParagraph();

      const rows: Inline[][][] = [];
      let rowIndex = index + 2;
      for (; rowIndex < lines.length; rowIndex += 1) {
        const rowCells = splitTableRow(lines[rowIndex]);
        if (!rowCells) break;
        rows.push(tableCells(rowCells, headerCells.length));
      }

      blocks.push({
        kind: "table",
        header: tableCells(headerCells, headerCells.length),
        alignments,
        rows,
      });
      index = rowIndex - 1;
      continue;
    }

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
