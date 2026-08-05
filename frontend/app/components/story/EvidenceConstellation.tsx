"use client";

import { CSSProperties, RefObject } from "react";

import { useScrollProgress } from "../../lib/use-scroll-progress";

type Props = {
  target: RefObject<HTMLElement | null>;
};

function clamp(value: number) {
  return Math.min(Math.max(value, 0), 1);
}

export function EvidenceConstellation({ target }: Props) {
  const progress = useScrollProgress(target);
  const connect = clamp((progress - 0.12) / 0.52);
  const converge = clamp((progress - 0.58) / 0.42);
  const style = {
    "--constellation-progress": progress,
    "--constellation-connect": connect,
    "--constellation-converge": converge,
    "--constellation-dash": `${(1 - connect) * 260}`,
    "--constellation-drift-x": `${(1 - connect) * 22}px`,
    "--constellation-drift-y": `${(1 - converge) * 28}px`,
  } as CSSProperties;

  return (
    <div className="evidence-constellation" style={style} aria-hidden="true">
      <svg viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
        <g className="constellation-particles">
          <circle cx="118" cy="144" r="2" />
          <circle cx="282" cy="76" r="1.5" />
          <circle cx="464" cy="184" r="2.5" />
          <circle cx="672" cy="102" r="1.5" />
          <circle cx="986" cy="138" r="2" />
          <circle cx="1262" cy="88" r="1.5" />
          <circle cx="1340" cy="326" r="2.5" />
          <circle cx="1216" cy="652" r="2" />
          <circle cx="950" cy="766" r="1.5" />
          <circle cx="598" cy="810" r="2" />
          <circle cx="274" cy="732" r="1.5" />
          <circle cx="92" cy="532" r="2.5" />
        </g>

        <g className="constellation-links">
          <path d="M118 144C284 188 348 312 506 354" />
          <path d="M282 76C408 164 454 264 594 338" />
          <path d="M1262 88C1110 156 1048 272 882 348" />
          <path d="M1340 326C1178 342 1068 372 910 408" />
          <path d="M92 532C258 526 368 500 526 454" />
          <path d="M274 732C408 630 492 568 612 502" />
          <path d="M1216 652C1068 594 978 536 860 480" />
        </g>

        <g className="constellation-documents">
          <g transform="translate(178 286) rotate(-5)">
            <rect width="118" height="152" rx="10" />
            <path d="M22 35h70M22 57h52M22 79h64M22 112h40" />
          </g>
          <g transform="translate(1134 232) rotate(5)">
            <rect width="118" height="152" rx="10" />
            <path d="M22 35h70M22 57h52M22 79h64M22 112h40" />
          </g>
          <g transform="translate(1030 632) rotate(-3)">
            <rect width="104" height="134" rx="10" />
            <path d="M20 32h62M20 53h46M20 74h56M20 101h34" />
          </g>
        </g>

        <g className="constellation-convergence">
          <path d="M506 354C604 378 644 418 720 450" />
          <path d="M594 338C646 374 684 412 720 450" />
          <path d="M882 348C810 382 770 416 720 450" />
          <path d="M910 408C822 420 772 434 720 450" />
          <path d="M526 454C606 452 664 451 720 450" />
          <path d="M612 502C652 484 688 466 720 450" />
          <path d="M860 480C806 468 760 458 720 450" />
          <circle cx="720" cy="450" r="11" />
          <circle className="constellation-core-ring" cx="720" cy="450" r="34" />
        </g>
      </svg>
    </div>
  );
}
