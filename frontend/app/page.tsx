"use client";

import Image from "next/image";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

type Message = {
  role: "assistant" | "user";
  content: string;
};

type AgentStreamEvent = {
  event: "status" | "token" | "result" | "error";
  data: Record<string, unknown>;
};

const statusMessage: Record<string, string> = {
  analyze: "질문과 조건을 살펴보는 중",
  tools: "법령과 상품 정보를 조회하는 중",
  generate: "답변을 작성하는 중",
  clarify: "추천 조건을 확인하는 중",
  out_of_scope: "도움드릴 수 있는 범위를 확인하는 중",
};

function createThreadId() {
  return crypto.randomUUID();
}

function parseSseEvent(block: string): AgentStreamEvent | null {
  const event = block.match(/^event: (.+)$/m)?.[1];
  const data = block.match(/^data: (.+)$/m)?.[1];

  if (!event || !data) return null;

  try {
    return { event: event as AgentStreamEvent["event"], data: JSON.parse(data) };
  } catch {
    return null;
  }
}

const questions = [
  "목돈을 모으기 위한 금융상품을 추천해 주세요.",
  "은행이 파산하면 내 예금은 얼마까지 보호받나요?",
  "예금자보호제도는 무엇인가요?",
];

const welcomeMessage: Message = {
  role: "assistant",
  content: "안녕하세요. 금융상품 조건과 소비자보호 법령을 함께 안내해 드려요. 원하는 상품이나 궁금한 상황을 남겨 주세요.",
};

export default function Home() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);
  const [threadId, setThreadId] = useState(createThreadId);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const messageList = messagesRef.current;
    if (!messageList) return;

    const frame = requestAnimationFrame(() => {
      messageList.scrollTo({
        top: messageList.scrollHeight,
        behavior: isLoading ? "auto" : "smooth",
      });
    });

    return () => cancelAnimationFrame(frame);
  }, [messages, isLoading, error]);

  useEffect(() => {
    const messageList = messagesRef.current;
    if (!messageList) return;

    const observer = new ResizeObserver(() => {
      messageList.scrollTop = messageList.scrollHeight;
    });
    observer.observe(messageList);

    return () => observer.disconnect();
  }, []);

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submittedQuestion = question.trim();
    if (!submittedQuestion || isLoading) return;

    setQuestion("");
    setError("");
    setIsLoading(true);
    setProgress("질문을 분석하는 중");
    setMessages((current) => [
      ...current,
      { role: "user", content: submittedQuestion },
      { role: "assistant", content: "" },
    ]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: submittedQuestion, threadId }),
      });
      if (!response.ok) throw new Error(await response.text());
      if (!response.body) throw new Error("스트리밍 응답을 읽을 수 없습니다.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let answer = "";
      let eventBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        eventBuffer += decoder.decode(value, { stream: true });
        const eventBlocks = eventBuffer.split("\n\n");
        eventBuffer = eventBlocks.pop() ?? "";

        eventBlocks.forEach((block) => {
          const streamEvent = parseSseEvent(block);
          if (!streamEvent) return;

          if (streamEvent.event === "status") {
            const stage = typeof streamEvent.data.stage === "string" ? streamEvent.data.stage : "";
            setProgress(statusMessage[stage] ?? "답변을 준비하는 중");
          }

          if (streamEvent.event === "token") {
            const text = typeof streamEvent.data.text === "string" ? streamEvent.data.text : "";
            answer += text;
            setMessages((current) => [
              ...current.slice(0, -1),
              { role: "assistant", content: answer },
            ]);
          }

          if (streamEvent.event === "result" && !answer) {
            const finalAnswer = typeof streamEvent.data.answer === "string"
              ? streamEvent.data.answer
              : "";
            if (finalAnswer) {
              answer = finalAnswer;
              setMessages((current) => [
                ...current.slice(0, -1),
                { role: "assistant", content: answer },
              ]);
            }
          }

          if (streamEvent.event === "error") {
            const message = typeof streamEvent.data.message === "string"
              ? streamEvent.data.message
              : "답변을 준비하지 못했습니다.";
            throw new Error(message);
          }
        });
      }

      if (!answer) throw new Error("Agent가 빈 응답을 보냈습니다.");
    } catch (cause) {
      setMessages((current) => current.slice(0, -1));
      setError(cause instanceof Error ? cause.message : "답변을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
      setProgress("");
    }
  }

  function startNewConversation() {
    if (isLoading) return;

    setThreadId(createThreadId());
    setMessages([welcomeMessage]);
    setQuestion("");
    setError("");
  }

  function submitOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <main className="page">
      <header className="topbar">
        <a className="brand" href="#" aria-label="금융안심 홈">
          <span className="brandMark">
            <Image src="/financial-guardian.png" alt="" width={40} height={40} priority />
          </span>
          금융안심
        </a>
        <span className="preview">TRUSTED GUIDE · 03</span>
      </header>

      <section className="intro">
        <p className="eyebrow">FINANCIAL GUIDE / 상품 · 법령 상담</p>
        <h1>
          <span className="headlineLine">불안한 금융 질문을,</span>
          <span className="headlineLine">조문부터 차분하게.</span>
        </h1>
        <p className="lede">예·적금 조건을 함께 확인하고, 금융소비자 권리를 현재 수집된 법령 근거로 쉽게 안내합니다.</p>
        <div className="scope">
          <span>예금자보호법</span>
          <span>금융소비자 보호에 관한 법률</span>
        </div>
      </section>

      <section className="chat" aria-label="금융상품 및 법령 상담">
        <div className="chatHead">
          <div><strong>금융상품 · 법령 안내</strong><small>학습·시연용 상담</small></div>
          <span className="status">{isLoading ? progress : "질문 입력 가능"}</span>
        </div>

        <div
          className="messages"
          data-testid="message-list"
          ref={messagesRef}
          aria-live="polite"
          aria-busy={isLoading}
        >
          {messages.map((message, index) => (
            <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
              <span className={`avatar ${message.role === "assistant" ? "assistantAvatar" : ""}`}>
                {message.role === "assistant"
                  ? <Image src="/financial-guardian.png" alt="" width={40} height={40} />
                  : "나"}
              </span>
              <p>{message.content || "법령에서 근거 조문을 찾고 있어요…"}</p>
            </article>
          ))}
        </div>

        {messages.length === 1 && <div className="examples">
          <p>이런 질문으로 시작할 수 있어요</p>
          {questions.map((suggestedQuestion, index) => (
            <button
              type="button"
              key={suggestedQuestion}
              onClick={() => setQuestion(suggestedQuestion)}
              disabled={isLoading}
            >
              <b>0{index + 1}</b>{suggestedQuestion}
            </button>
          ))}
        </div>}

        <form className="composer" onSubmit={submitQuestion}>
          <textarea
            aria-label="상담 질문"
            placeholder="질문을 입력해 주세요"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={submitOnEnter}
            disabled={isLoading}
            maxLength={500}
            rows={2}
          />
          <button type="submit" disabled={!question.trim() || isLoading} aria-label="질문 보내기">→</button>
        </form>
        <button type="button" className="newConversation" onClick={startNewConversation} disabled={isLoading}>
          새 대화 시작
        </button>
        {error && <p className="error" role="alert">{error}</p>}
        <p className="notice">조건이 부족하면 추가 질문을 드립니다. 최종 가입 전에는 금융회사 상품설명서와 최신 공식 공시를 확인해 주세요.</p>
      </section>
    </main>
  );
}
