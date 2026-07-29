"use client";

import Image from "next/image";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

type Message = {
  role: "assistant" | "user";
  content: string;
};

const questions = [
  "은행이 파산하면 내 예금은 얼마까지 보호받나요?",
  "예금자보호제도는 무엇인가요?",
  "금융상품 설명을 제대로 듣지 못했다면 어떻게 해야 하나요?",
];

const welcomeMessage: Message = {
  role: "assistant",
  content: "안녕하세요. 궁금한 상황을 남겨 주세요. 관련 법령의 근거를 먼저 찾고, 핵심만 쉽게 설명해 드릴게요.",
};

export default function Home() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);
  const [isLoading, setIsLoading] = useState(false);
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
    setMessages((current) => [
      ...current,
      { role: "user", content: submittedQuestion },
      { role: "assistant", content: "" },
    ]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: submittedQuestion }),
      });
      if (!response.ok) throw new Error(await response.text());
      if (!response.body) throw new Error("스트리밍 응답을 읽을 수 없습니다.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let answer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        answer += decoder.decode(value, { stream: true });
        setMessages((current) => [
          ...current.slice(0, -1),
          { role: "assistant", content: answer },
        ]);
      }

      answer += decoder.decode();
      if (!answer) throw new Error("법령 답변 서버가 빈 응답을 보냈습니다.");
    } catch (cause) {
      setMessages((current) => current.slice(0, -1));
      setError(cause instanceof Error ? cause.message : "답변을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
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
        <p className="eyebrow">FINANCIAL LAW DESK / 법령 상담</p>
        <h1>
          <span className="headlineLine">불안한 금융 질문을,</span>
          <span className="headlineLine">조문부터 차분하게.</span>
        </h1>
        <p className="lede">예금자보호와 금융소비자 권리를 현재 수집된 법령 안에서 찾아 쉬운 말로 안내합니다.</p>
        <div className="scope"><span>예금자보호법</span><span>금융소비자보호법</span></div>
      </section>

      <section className="chat" aria-label="법령 상담">
        <div className="chatHead">
          <div><strong>법령 안내 데스크</strong><small>학습·시연용 상담</small></div>
          <span className="status">{isLoading ? "근거 검색 중" : "질문 입력 가능"}</span>
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
        {error && <p className="error" role="alert">{error}</p>}
        <p className="notice">답변을 받으려면 FastAPI와 Ollama가 실행 중이어야 합니다. 최신 법령과 공식 공시를 다시 확인해 주세요.</p>
      </section>
    </main>
  );
}
