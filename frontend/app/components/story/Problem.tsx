"use client";

import { useRef } from "react";

import { storyPhaseAt, storyPhaseProgress } from "../../lib/story-state";
import { useScrollProgress } from "../../lib/use-scroll-progress";

const STORY_PHASES = [
  {
    eyebrow: "01 · 흩어진 정보",
    title: "답을 찾으려면\n서로 다른 곳을 뒤져야 합니다.",
    detail: "법령, 공시, 상품설명서는 같은 질문의 답을 서로 다른 방식으로 담고 있습니다.",
  },
  {
    eyebrow: "02 · 근거 찾기",
    title: "질문에 맞는 기준을\n하나씩 확인합니다.",
    detail: "보호 범위와 상품 조건처럼 판단에 필요한 정보만 찾아 연결합니다.",
  },
  {
    eyebrow: "03 · 이해할 수 있는 답",
    title: "찾은 근거와 함께\n내 상황에 맞춰 설명합니다.",
    detail: "무엇을 확인했는지와 다음에 살펴볼 내용을 한 화면에서 확인할 수 있습니다.",
  },
];

const SOURCE_CARDS = [
  { kind: "법령", title: "예금자보호법", detail: "보호 범위" },
  { kind: "공시", title: "금융상품 공시", detail: "금리와 조건" },
  { kind: "설명서", title: "상품설명서", detail: "권리와 유의사항" },
];

export function Problem() {
  const sectionRef = useRef<HTMLElement>(null);
  const progress = useScrollProgress(sectionRef);
  const phase = storyPhaseAt(progress);
  const phaseProgress = storyPhaseProgress(progress, phase);
  const currentPhase = STORY_PHASES[phase];

  return (
    <section
      className="story-scroll"
      id="problem"
      ref={sectionRef}
      data-stage={phase}
      style={{ "--story-progress": progress, "--phase-progress": phaseProgress } as React.CSSProperties}
    >
      <div className="story-scene">
        <div className="story-inner story-journey">
          <div className="journey-copy">
            <div className="journey-copy-text" key={phase}>
              <p className="scene-label">{currentPhase.eyebrow}</p>
              <h2>
                {currentPhase.title.split("\n").map((line, index) => (
                  <span key={line}>
                    {index > 0 && <br />}
                    {line}
                  </span>
                ))}
              </h2>
              <p className="journey-lede">{currentPhase.detail}</p>
            </div>

            <ol className="journey-stepper" aria-label="핀봄의 답변 과정">
              {STORY_PHASES.map((item, index) => (
                <li key={item.eyebrow} data-active={index === phase}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <p>{item.eyebrow.replace(/^\d+ · /, "")}</p>
                </li>
              ))}
            </ol>
          </div>

          <div className="journey-visual" aria-hidden="true">
            <div className="journey-routes">
              <span className="journey-route journey-route-a" />
              <span className="journey-route journey-route-b" />
              <span className="journey-route journey-route-c" />
            </div>

            {SOURCE_CARDS.map((source, index) => (
              <article className={`journey-document journey-document-${index + 1}`} key={source.kind}>
                <span>{source.kind}</span>
                <strong>{source.title}</strong>
                <small>{source.detail}</small>
              </article>
            ))}

            <div className="journey-core">
              <span>질문</span>
              <strong>
                내 예금은
                <br />
                어디까지?
              </strong>
            </div>

            <div className="journey-answer-card">
              <span>확인한 근거</span>
              <strong>예금자보호법 제32조</strong>
              <p>보호 범위와 확인 방법을 정리했어요.</p>
            </div>
          </div>

          <ol className="journey-mobile-summary">
            {STORY_PHASES.map((item, index) => (
              <li key={item.eyebrow}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{item.eyebrow.replace(/^\d+ · /, "")}</strong>
                  <p>{item.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
