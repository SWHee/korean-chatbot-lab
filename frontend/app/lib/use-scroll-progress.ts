"use client";

import { RefObject, useEffect, useState } from "react";

/**
 * 대상 구간을 지나는 동안의 스크롤 진행도 0~1.
 * scroll hijacking 없이 브라우저 기본 스크롤 위치만 읽는다.
 */
export function useScrollProgress(ref: RefObject<HTMLElement | null>) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    let frame = 0;

    const measure = () => {
      frame = 0;
      const { top, height } = element.getBoundingClientRect();
      const scrollable = height - window.innerHeight;
      if (scrollable <= 0) {
        setProgress(0);
        return;
      }
      const nextProgress = Math.min(Math.max(-top / scrollable, 0), 1);
      setProgress((current) => (Math.abs(current - nextProgress) >= 0.002 ? nextProgress : current));
    };

    // 스크롤 이벤트마다 계산하지 않고 다음 프레임에 한 번만 모아서 처리
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };

    measure();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);

    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [ref]);

  return progress;
}
