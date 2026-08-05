"use client";

import Image from "next/image";

import { ChevronDownIcon } from "../icons";
import { useReveal } from "../../lib/use-reveal";

export function Hero() {
  const { ref, revealed } = useReveal<HTMLElement>(0.1);

  return (
    <section className="story-section hero" ref={ref}>
      <div className="story-inner">
        <div className="hero-copy">
          <p className="reveal hero-eyebrow" data-revealed={revealed} style={{ "--i": 0 } as React.CSSProperties}>
            핀봄
          </p>
          <h1 className="reveal" data-revealed={revealed} style={{ "--i": 1 } as React.CSSProperties}>
            금융 질문이 어려운 이유는,
            <br />
            답보다 <em>근거</em>를 찾기 어렵기 때문입니다.
          </h1>
          <p className="reveal hero-lede" data-revealed={revealed} style={{ "--i": 2 } as React.CSSProperties}>
            핀봄은 법령과 상품 정보를 확인하고 근거와 함께 설명합니다.
          </p>
          <div className="hero-actions reveal" data-revealed={revealed} style={{ "--i": 3 } as React.CSSProperties}>
            <a className="hero-primary" href="#chat">
              바로 상담하기
            </a>
            <a className="scroll-cue" href="#problem">
              먼저 알아보기
              <ChevronDownIcon />
            </a>
          </div>
        </div>

        <div className="hero-visual reveal" data-revealed={revealed} style={{ "--i": 2 } as React.CSSProperties}>
          <span className="hero-orbit hero-orbit-outer" aria-hidden="true" />
          <span className="hero-orbit hero-orbit-inner" aria-hidden="true" />
          <Image
            className="hero-character"
            src="/brand/financial-guide-waving-v2.png"
            alt="금융 질문을 안내하는 핀봄 마스코트 포키"
            width={1254}
            height={1254}
            loading="eager"
            priority
            unoptimized
          />
        </div>
      </div>
    </section>
  );
}
