import Link from "next/link";
import { copy } from "@/lib/copy";
import { RETENTION_DAYS } from "@/lib/legal";
import { addDays, aiSummary, formatTime, type Receipt } from "@/lib/receipt";

/** 這次健檢的資料處理紀錄：下載、刪除、送給誰、保存多久。 */
export function ReceiptPanel({ receipt }: { receipt: Receipt }) {
  const r = copy.receipt;
  const ai = aiSummary(receipt.calls);
  const keepDays = receipt.mode === "quick" ? 7 : RETENTION_DAYS;
  const rows: [string, string][] = [
    [r.download, `${formatTime(receipt.startedAt) ?? r.atStart}　${receipt.mode === "quick" ? r.downloadQuick : r.downloadApp}`],
    [r.deleted, `${formatTime(receipt.finishedAt) ?? r.atEnd}　${r.deletedNote}`],
    [r.ai, ai.length
      ? ai.map((a) => r.aiLine(a.label, a.requests, a.tokens.toLocaleString())).join("；") + `　${r.aiNote}`
      : r.noAi],
    [r.kept, `${formatTime(addDays(receipt.finishedAt, keepDays)) ?? r.keptDays(keepDays)}　${receipt.mode === "quick" ? r.keptQuick : r.keptApp}`],
  ];
  return (
    <section className="flex flex-col gap-3 rounded-card border border-healthy/40 bg-surface p-5">
      <h2 className="font-bold">{r.title}{receipt.mode === "demo" && <span className="ml-2 text-xs font-normal text-muted">{r.demo}</span>}</h2>
      <dl className="grid gap-2 text-sm sm:grid-cols-[8rem_1fr]">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="flex items-start gap-2 text-muted"><span aria-hidden className="text-healthy">✓</span>{k}</dt>
            <dd className="leading-relaxed">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-muted">{r.footer} <Link href="/security" className="text-primary underline-offset-4 hover:underline">{r.verify}</Link></p>
    </section>
  );
}
