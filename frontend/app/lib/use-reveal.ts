"use client";

import { useEffect, useRef, useState } from "react";

/**
 * 화면에 들어오면 한 번만 true가 되는 등장 플래그.
 * 되돌아 올라갈 때 다시 사라지면 산만해서 되돌리지 않는다.
 */
export function useReveal<T extends HTMLElement>(threshold = 0.25) {
  const ref = useRef<T>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { threshold },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, revealed };
}
