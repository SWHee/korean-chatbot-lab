"use client";

import { useRef } from "react";

import { ChatConsole } from "./components/ChatConsole";
import { EvidenceConstellation } from "./components/story/EvidenceConstellation";
import { Hero } from "./components/story/Hero";
import { Problem } from "./components/story/Problem";
import { ScrollProgressBar } from "./components/story/ScrollProgressBar";

export default function Home() {
  const storyRef = useRef<HTMLDivElement>(null);

  return (
    <main className="experience">
      <EvidenceConstellation target={storyRef} />
      <ScrollProgressBar target={storyRef} />

      <div className="story" ref={storyRef}>
        <Hero />
        <Problem />
      </div>

      <section className="chat-section" id="chat">
        <div className="chat-intro">
          <h2>이제, 내 상황을 물어보세요.</h2>
          <p>질문을 남기면 관련 법령과 상품 정보를 확인해 근거와 함께 답해 드립니다.</p>
        </div>
        <ChatConsole />
      </section>
    </main>
  );
}
