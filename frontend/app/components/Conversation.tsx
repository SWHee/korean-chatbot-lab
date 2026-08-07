"use client";

import { AnswerMarkdown } from "./AnswerMarkdown";
import { BrandLogo } from "./BrandLogo";
import { AlertIcon, ArrowRightIcon } from "./icons";

export type Turn = {
  role: "user" | "assistant";
  content: string;
};

const SEED_QUESTIONS = [
  "은행이 파산하면 내 예금은 얼마까지 보호받나요?",
  "1년 동안 가입할 예금·적금 상품을 비교해 주세요.",
  "가입 후 마음이 바뀌면 청약을 철회할 수 있나요?",
];

type Props = {
  turns: Turn[];
  isStreaming: boolean;
  waitingMessage: string;
  error: string;
  onSeedClick: (question: string) => void;
  onHoverSource: (sourceId: string | null) => void;
};

export function Conversation({
  turns,
  isStreaming,
  waitingMessage,
  error,
  onSeedClick,
  onHoverSource,
}: Props) {
  if (turns.length === 0) {
    return (
      <div className="opening">
        <p className="opening-eyebrow">
          예·적금 상품 비교 · 예금자보호법 · 금융소비자보호법
        </p>
        <h1>
          금융 질문, <em>근거와 함께</em>
          <br />
          확인하세요.
        </h1>
        <p>
          예금·적금 상품을 비교하고, 예금이 얼마까지 보호되는지,
          <br className="opening-copy-break" />{" "}
          소비자로서 어떤 권리가 있는지 법령에서 찾아 쉽게 설명해 드려요.
          <br className="opening-copy-break" />{" "}
          답변 옆에는 상품 정보와 근거가 된 조문을 함께 보여 드려요.
        </p>

        <div className="seed-list">
          {SEED_QUESTIONS.map((question, index) => (
            <button
              className="seed"
              key={question}
              type="button"
              style={{ "--i": index } as React.CSSProperties}
              onClick={() => onSeedClick(question)}
              disabled={isStreaming}
            >
              <span className="seed-index">{index + 1}</span>
              <span>{question}</span>
              <ArrowRightIcon className="seed-arrow" />
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      {turns.map((turn, index) => {
        if (turn.role === "user") {
          return (
            <article className="turn" key={index} data-role="user">
              <p className="user-card">{turn.content}</p>
            </article>
          );
        }

        const isLast = index === turns.length - 1;

        return (
          <article className="turn" key={index} data-role="assistant">
            <div className="bot-head">
              <BrandLogo variant="avatar" />
              <span className="bot-name">포키</span>
            </div>
            <div className="bot-body">
              {turn.content ? (
                <AnswerMarkdown
                  content={turn.content}
                  isStreaming={isLast && isStreaming}
                  onHoverSource={onHoverSource}
                />
              ) : (
                <p className="pending">{waitingMessage}</p>
              )}
            </div>
          </article>
        );
      })}

      {error && (
        <p className="alert" role="alert">
          <AlertIcon />
          {error}
        </p>
      )}
    </>
  );
}
