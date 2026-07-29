import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "금융안심 | 법령 상담",
  description: "예금자보호와 금융소비자 권리를 법령에서 찾아 설명하는 상담 UI",
  icons: {
    icon: "/financial-guardian.png",
    apple: "/financial-guardian.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
