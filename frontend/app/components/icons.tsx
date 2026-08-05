/** 화면에서 쓰는 SVG 아이콘 (이모지 대신 사용) */

type IconProps = { className?: string };

function Stroke({ children, className }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/** 상담 말풍선 안의 확인 표시 — 헤더 로고와 답변 아바타가 함께 쓰는 마크 */
export function BrandMark({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M20.5 11.2c0 4.1-3.8 7.5-8.5 7.5-.85 0-1.68-.11-2.45-.32L4.8 20.8l1.35-3.8C4.4 15.6 3.5 13.5 3.5 11.2c0-4.1 3.8-7.5 8.5-7.5s8.5 3.4 8.5 7.5Z" />
      <path d="m8.7 11 2.3 2.3 4.4-4.5" strokeWidth="2" />
    </Stroke>
  );
}

export function SunIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </Stroke>
  );
}

export function MoonIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </Stroke>
  );
}

export function ArrowUpIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M12 19V5m-7 7 7-7 7 7" />
    </Stroke>
  );
}

export function ChevronDownIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="m6 9 6 6 6-6" />
    </Stroke>
  );
}

export function ArrowRightIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M5 12h14m-7-7 7 7-7 7" />
    </Stroke>
  );
}

export function RestartIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </Stroke>
  );
}

export function AlertIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <path d="M12 9v4M12 17h.01" />
    </Stroke>
  );
}
