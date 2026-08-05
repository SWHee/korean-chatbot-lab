import Image from "next/image";

type Props = {
  /** header = 상단 로고, avatar = 답변 옆 아바타 */
  variant?: "header" | "avatar";
};

/**
 * 히어로 캐릭터 원본을 헤더와 답변 프로필에서도 같은 얼굴로 잘라 사용.
 */
export function BrandLogo({ variant = "header" }: Props) {
  return (
    <span className={variant === "header" ? "brand-mark" : "bot-avatar"} aria-hidden="true">
      <Image
        className="brand-character"
        src="/brand/financial-guide-waving-v2.png"
        alt=""
        width={1254}
        height={1254}
        loading="eager"
        unoptimized
      />
    </span>
  );
}
