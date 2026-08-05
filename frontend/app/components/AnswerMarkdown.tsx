"use client";

import { Block, Inline, parseBlocks } from "../lib/answer-format";

type HoverSource = (sourceId: string | null) => void;

/** 인라인 조각 — [S1] 표기는 우측 근거 카드와 연동되는 칩으로 표시 */
function InlineParts({
  parts,
  onHoverSource,
}: {
  parts: Inline[];
  onHoverSource: HoverSource;
}) {
  return (
    <>
      {parts.map((part, index) => {
        if (part.kind === "strong") return <strong key={index}>{part.text}</strong>;
        if (part.kind === "citation") {
          return (
            <button
              className="citation"
              key={index}
              type="button"
              aria-label={`근거 ${part.sourceId} 강조`}
              onMouseEnter={() => onHoverSource(part.sourceId)}
              onMouseLeave={() => onHoverSource(null)}
              onFocus={() => onHoverSource(part.sourceId)}
              onBlur={() => onHoverSource(null)}
            >
              {part.sourceId}
            </button>
          );
        }
        return <span key={index}>{part.text}</span>;
      })}
    </>
  );
}

/** 스트리밍 중에는 마지막 블록 끝에 커서를 붙여 생성 중임을 표시 */
const Caret = () => <span className="caret" aria-hidden="true" />;

function BlockView({
  block,
  withCaret,
  onHoverSource,
}: {
  block: Block;
  withCaret: boolean;
  onHoverSource: HoverSource;
}) {
  if (block.kind === "heading") {
    const Tag = block.level === 2 ? "h3" : "h4";
    return (
      <Tag>
        <InlineParts parts={block.content} onHoverSource={onHoverSource} />
        {withCaret && <Caret />}
      </Tag>
    );
  }

  if (block.kind === "list") {
    const Tag = block.ordered ? "ol" : "ul";
    return (
      <Tag>
        {block.items.map((item, index) => (
          <li key={index}>
            <InlineParts parts={item} onHoverSource={onHoverSource} />
            {withCaret && index === block.items.length - 1 && <Caret />}
          </li>
        ))}
      </Tag>
    );
  }

  return (
    <p>
      <InlineParts parts={block.content} onHoverSource={onHoverSource} />
      {withCaret && <Caret />}
    </p>
  );
}

/** Agent가 Markdown으로 내려 주는 답변 본문 렌더링 */
export function AnswerMarkdown({
  content,
  isStreaming,
  onHoverSource,
}: {
  content: string;
  isStreaming: boolean;
  onHoverSource: HoverSource;
}) {
  const blocks = parseBlocks(content);

  return (
    <div className="answer">
      {blocks.map((block, index) => (
        <BlockView
          key={index}
          block={block}
          withCaret={isStreaming && index === blocks.length - 1}
          onHoverSource={onHoverSource}
        />
      ))}
    </div>
  );
}
