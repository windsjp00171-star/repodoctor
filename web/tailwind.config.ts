import type { Config } from "tailwindcss";

// 顏色只用設計 token（SPEC：元件裡不出現寫死的色碼）。值定義在 app/globals.css。
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        surface: token("surface"),
        border: token("border"),
        text: token("text"),
        muted: token("text-muted"),
        primary: token("primary"),
        critical: token("critical"),
        high: token("high"),
        medium: token("medium"),
        healthy: token("healthy"),
      },
      borderRadius: { card: "12px" },
      fontFamily: {
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        num: ["var(--font-num)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
