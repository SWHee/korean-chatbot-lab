"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import { BrandLogo } from "./BrandLogo";
import { Conversation, Turn } from "./Conversation";
import { EvidencePanel } from "./EvidencePanel";
import { EvidencePending } from "./EvidencePending";
import { AlertIcon, ArrowUpIcon, RestartIcon } from "./icons";
import { AgentResult, Stage, WAITING_MESSAGE, readAgentStream } from "../lib/agent-stream";
import { getWorkspaceMode } from "../lib/workspace-mode";

const MAX_QUESTION_LENGTH = 500;
const DEFAULT_WAITING_MESSAGE = "질문을 살펴보고 있어요";

export function ChatConsole() {
  const [threadId, setThreadId] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeStage, setActiveStage] = useState<Stage | null>(null);
  const [latestResult, setLatestResult] = useState<AgentResult | null>(null);
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const transcriptRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const waitingMessage = activeStage
    ? WAITING_MESSAGE[activeStage]
    : DEFAULT_WAITING_MESSAGE;

  // 근거가 실제로 있을 때만 오른쪽 패널을 연다
  const evidenceResult =
    latestResult && (latestResult.sources.length > 0 || latestResult.products.length > 0)
      ? latestResult
      : null;
  const workspaceMode = getWorkspaceMode({
    hasTurns: turns.length > 0,
    isStreaming,
    hasEvidence: evidenceResult !== null,
    hasError: Boolean(error),
  });

  // thread id는 hydration 불일치를 피해 마운트 뒤에 생성
  useEffect(() => setThreadId(crypto.randomUUID()), []);

  // 대화 목록 안에서만 스크롤을 움직여 페이지 스크롤을 끌지 않는다
  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript) return;
    transcript.scrollTo({
      top: transcript.scrollHeight,
      behavior: isStreaming ? "auto" : "smooth",
    });
  }, [turns, isStreaming, error]);

  // 입력 줄 수에 맞춰 높이 조절
  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${input.scrollHeight}px`;
  }, [draft]);

  async function runTurn(question: string) {
    setDraft("");
    setError("");
    setIsStreaming(true);
    setActiveStage(null);
    setLatestResult(null);
    setActiveSourceId(null);
    setTurns((current) => [
      ...current,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);

    const updateAnswer = (content: string) =>
      setTurns((current) => [...current.slice(0, -1), { role: "assistant", content }]);

    let answer = "";

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, threadId }),
      });
      if (!response.ok) throw new Error(await response.text());
      if (!response.body) throw new Error("스트리밍 응답을 읽을 수 없습니다.");

      for await (const streamEvent of readAgentStream(response.body)) {
        if (streamEvent.event === "status") setActiveStage(streamEvent.stage);

        if (streamEvent.event === "token") {
          answer += streamEvent.text;
          updateAnswer(answer);
        }

        if (streamEvent.event === "result") {
          answer = answer || streamEvent.result.answer;
          setLatestResult(streamEvent.result);
          updateAnswer(answer);
        }

        if (streamEvent.event === "error") throw new Error(streamEvent.message);
      }

      if (!answer) throw new Error("답변을 받지 못했어요. 잠시 후 다시 시도해 주세요.");
    } catch (cause) {
      setTurns((current) => current.slice(0, -1));
      setError(cause instanceof Error ? cause.message : "답변을 불러오지 못했습니다.");
    } finally {
      setIsStreaming(false);
      setActiveStage(null);
    }
  }

  // 추천 질문은 바로 보내지 않고 입력창을 채워 사용자가 고칠 수 있게 한다
  function fillDraft(question: string) {
    setDraft(question);
    inputRef.current?.focus();
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || isStreaming || !threadId) return;
    void runTurn(question);
  }

  function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function startNewThread() {
    if (isStreaming) return;
    setThreadId(crypto.randomUUID());
    setTurns([]);
    setDraft("");
    setError("");
    setLatestResult(null);
    setActiveSourceId(null);
  }

  return (
    <div className="chat-app">
      <header className="topbar">
        <div className="brand">
          <BrandLogo />
          <div>
            <span className="brand-name">핀봄</span>
            <span className="brand-sub">예금자보호 · 금융소비자 상담</span>
          </div>
        </div>

        <span className="topbar-spacer" />

        <button
          className="ghost-button"
          type="button"
          onClick={startNewThread}
          disabled={isStreaming}
        >
          <RestartIcon />
          새 상담
        </button>
      </header>

      <main className="workspace" data-workspace-mode={workspaceMode}>
        <section className="conversation">
          {/* 토큰 단위로 읽히지 않도록, 진행 상황만 별도 영역에서 알림 */}
          <p className="sr-only" role="status">
            {isStreaming
              ? waitingMessage
              : latestResult
                ? `답변이 도착했어요. 법령 조문 ${latestResult.sources.length}건을 근거로 했습니다.`
                : ""}
          </p>

          <div className="transcript scroll" ref={transcriptRef}>
            <div className="transcript-inner">
              <Conversation
                turns={turns}
                isStreaming={isStreaming}
                waitingMessage={waitingMessage}
                error={error}
                onSeedClick={fillDraft}
                onHoverSource={setActiveSourceId}
              />
            </div>
          </div>

          <div className="composer-area">
            <form className="composer" onSubmit={submit}>
              <textarea
                ref={inputRef}
                aria-label="상담 질문"
                placeholder="예금자보호 한도, 청약 철회, 정기예금 금리처럼 궁금한 상황을 적어 주세요."
                value={draft}
                rows={1}
                maxLength={MAX_QUESTION_LENGTH}
                disabled={isStreaming}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={submitOnEnter}
              />
              <button
                className="send"
                type="submit"
                aria-label="질문 보내기"
                disabled={!draft.trim() || isStreaming || !threadId}
              >
                <ArrowUpIcon />
              </button>
            </form>
            <div className="composer-hint">
              <span>Enter 전송 · Shift+Enter 줄바꿈</span>
              <span>
                {draft.length}/{MAX_QUESTION_LENGTH}
              </span>
            </div>
          </div>
        </section>

        {workspaceMode === "searching" && <EvidencePending message={waitingMessage} />}
        {evidenceResult && (
          <EvidencePanel result={evidenceResult} activeSourceId={activeSourceId} />
        )}
      </main>

      <footer className="disclaimer">
        <AlertIcon />
        본 서비스의 답변과 표시된 법령·공시 정보는 참고용이며, 법적 효력이나 법률·금융
        자문을 제공하지 않습니다. 최신 내용과 실제 가입·보호 여부는 관계 기관과 해당
        금융회사에서 확인해 주세요.
      </footer>
    </div>
  );
}
