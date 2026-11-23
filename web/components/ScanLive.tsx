"use client";
import { copy } from "@/lib/copy";
import type { ScanRow } from "@/lib/types";

/** 掃描中（SPEC 標誌時刻 1）：一道掃描光、真的進度、真的檔名、即時的問題數。 */
export function ScanLive({ project, scan, recentFiles }: { project: string; scan: ScanRow; recentFiles: string[] }) {
  const progress = { progress: scan.progress, stage: scan.status === "queued" ? "排隊中，馬上輪到你" : scan.stage ?? "", found: scan.found };
  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-primary">{copy.scanning.title}</div>
          <h1 className="text-2xl font-bold">{project}</h1>
          <p className="mt-1 text-sm text-muted">{progress.stage}</p>
        </div>
        <div className="text-right">
          <div className="font-num text-4xl font-bold tabular-nums">{progress.found}</div>
          <div className="text-xs text-muted">{copy.scanning.found}</div>
        </div>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-border" role="progressbar" aria-valuenow={progress.progress} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${progress.progress}%` }} />
      </div>

      <div className="relative overflow-hidden rounded-card border border-border bg-surface p-4">
        <div aria-hidden className="animate-scanline pointer-events-none absolute inset-x-0 top-0 h-full bg-gradient-to-b from-transparent via-primary/10 to-transparent" />
        <div className="mb-2 text-xs text-muted">{copy.scanning.files}</div>
        <ul className="flex flex-col gap-1 font-mono text-xs">
          {recentFiles.length === 0 && <li className="text-muted">…</li>}
          {recentFiles.map((f, i) => (
            <li key={f} className={`truncate ${i === 0 ? "text-primary" : "text-muted"}`} style={{ opacity: 1 - i * 0.07 }}>
              {i === 0 ? "▸ " : "  "}{f}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
