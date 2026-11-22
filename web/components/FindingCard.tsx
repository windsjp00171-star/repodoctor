"use client";
import { copy } from "@/lib/copy";
import type { Finding } from "@/lib/types";
import { CopyButton } from "./CopyButton";

const SEV_STYLE: Record<string, string> = {
  critical: "text-critical border-critical",
  high: "text-high border-high",
  medium: "text-medium border-medium",
  low: "text-muted border-border",
};
// 嚴重度不只靠顏色，也要有文字與圖示（SPEC 底線規則）
const SEV_ICON: Record<string, string> = { critical: "▲", high: "●", medium: "◆", low: "○" };

/** 說明文字裡的 `xxx` 顯示成程式碼樣式，不要讓使用者看到反引號。 */
function Inline({ text }: { text: string }) {
  return (
    <>
      {text.split(/(`[^`]+`)/).map((part, i) =>
        part.startsWith("`") && part.endsWith("`") && part.length > 2 ? (
          <code key={i} className="rounded bg-bg px-1 py-0.5 font-mono text-[0.85em] text-primary">{part.slice(1, -1)}</code>
        ) : (
          part
        ),
      )}
    </>
  );
}

export function FindingCard({ f, advanced, open }: { f: Finding; advanced: boolean; open?: boolean }) {
  const loc = f.file_path ? `${f.file_path}${f.line ? `：第 ${f.line} 行` : ""}` : null;
  return (
    <details open={open}
      className={`group rounded-card border bg-surface ${f.severity === "critical" ? "animate-critical border-critical/60" : "border-border"}`}>
      <summary className="grid cursor-pointer list-none grid-cols-[auto_1fr_auto] items-center gap-3 p-4 [&::-webkit-details-marker]:hidden">
        <span className={`whitespace-nowrap rounded border px-2 py-1 font-mono text-xs font-semibold ${SEV_STYLE[f.severity]}`}>
          {SEV_ICON[f.severity]} {copy.severities[f.severity]}
        </span>
        <span className="min-w-0 font-semibold">{f.title}</span>
        <span className="hidden whitespace-nowrap text-xs text-muted sm:inline">
          {copy.categories[f.category]}{f.source === "ai" ? "・AI" : ""}
        </span>
      </summary>
      <div className="flex flex-col gap-3 px-4 pb-4">
        <p className="leading-relaxed"><Inline text={f.plain_explanation} /></p>
        {advanced && (
          <div className="flex flex-col gap-2 text-sm text-muted">
            <p><Inline text={f.advanced_explanation} /></p>
            {loc && <p className="font-mono text-xs">{loc}</p>}
            {f.masked_snippet && <pre className="overflow-x-auto rounded-md border border-border bg-bg p-2 font-mono text-xs text-text">{f.masked_snippet}</pre>}
          </div>
        )}
        <div className="rounded-md border border-border bg-bg">
          <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2 text-xs text-muted">
            <span>{copy.report.fix}</span>
            <CopyButton text={f.fix_prompt} />
          </div>
          <pre className="whitespace-pre-wrap break-words p-3 font-sans text-sm leading-relaxed">{f.fix_prompt}</pre>
        </div>
      </div>
    </details>
  );
}
