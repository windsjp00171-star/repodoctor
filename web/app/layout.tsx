import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Noto_Sans_TC } from "next/font/google";
import { motionCssVars } from "@/lib/motion";
import "./globals.css";

const body = Noto_Sans_TC({ subsets: ["latin"], weight: ["400", "500", "700"], variable: "--font-body", display: "swap" });
const num = Inter({ subsets: ["latin"], variable: "--font-num", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = { title: "RepoDoctor", description: "你的程式健檢醫生" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant" className={`${body.variable} ${num.variable} ${mono.variable}`}>
      <body className="min-h-screen font-sans antialiased" style={motionCssVars}>
        <main className="mx-auto flex max-w-5xl flex-col gap-10 px-4 py-10 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
