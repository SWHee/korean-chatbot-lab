import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "핀봄 | 근거와 함께 확인하는 금융 상담",
  description:
    "예금자보호와 금융소비자 권리를 법령에서 찾아 근거와 함께 설명하는 상담 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <head>
        {/* 한글 금융 UI 기준 서체. 미설치 환경에서는 시스템 산세리프로 대체 */}
        <link rel="preconnect" href="https://cdn.jsdelivr.net" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
