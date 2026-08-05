"use client";

import { RefObject } from "react";

import { useScrollProgress } from "../../lib/use-scroll-progress";

/** 소개 구간에서만 보이는 2px 진행 표시줄. 상담 영역에 닿으면 사라진다. */
export function ScrollProgressBar({ target }: { target: RefObject<HTMLElement | null> }) {
  const progress = useScrollProgress(target);
  const visible = progress > 0.005 && progress < 0.995;

  return (
    <div
      className="scroll-progress"
      data-visible={visible}
      style={{ transform: `scaleX(${progress})` }}
      aria-hidden="true"
    />
  );
}
