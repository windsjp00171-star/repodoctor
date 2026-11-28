"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { allCriticalPrompt, copy, scoreContext } from "@/lib/copy";
import type { Previous } from "@/lib/improve";
import type { Receipt } from "@/lib/receipt";
import type { Report } from "@/lib/types";
import { BadgePanel } from "./BadgePanel";
import { CopyButton } from "./CopyButton";
import { FindingCard } from "./FindingCard";
import { ImprovePanel } from "./ImprovePanel";
import { ReceiptPanel } from "./ReceiptPanel";
import { ScoreRing } from "./ScoreRing";

const AI_CATS = new Set(["auth", "drift"]);

export function ReportView({ report, previous, onRescan, expired = false, repoId, receipt }: {
  report: Report; previous: Previous | null; onRescan: () => Promise<void>; expired?: boolean;
  repoId?: string;  // 有給才顯示「健檢徽章」（範例報告不給）
  receipt?: Receipt;  // 這次健檢的資料處理紀錄
}) {
  const [advanced, setAdvanced] = useState(false);
  const [rescanning, setRescanning] = useState(false);
  useEffect(() => {
    try {
      setAdvanced(localStorage.getItem("rd-mode") === "advanced");
    } catch {
      /* 無痕模式 */
    }
  }, []);
  const setMode = (adv: boolean) => {
    setAdvanced(adv);
    try {
      localStorage.setItem("rd-mode", adv ? "advanced" : "plain");
    } catch {
      /* 無痕模式 */
    }
  };
  async function rescan() {
    setRescanning(true);
    await onRescan();
    setRescanning(false);
  }

  const critical = report.findings.filter((f) => f.severity === "critical");
  const context = scoreContext(report);
  const cost = report.cost;
  const covStatus = (k: string) => report.coverage[k]?.status;

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <Link href="/dashboard" className="text-muted hover:text-text">← {copy.report.back}</Link>
        <div className="flex items-center gap-2">
          <div role="group" aria-label="報告模式" className="inline-flex rounded-full border border-border p-1">
            {[false, true].map((adv) => (
              <button key={String(adv)} type="button" aria-pressed={advanced === adv} onClick={() => setMode(adv)}
                className={`rounded-full px-3 py-1 ${advanced === adv ? "bg-primary/10 text-primary" : "text-muted"}`}>
                {adv ? copy.report.advanced : copy.report.plain}
              </button>
            ))}
          </div>
          <button type="button" onClick={rescan} disabled={rescanning}
            className="rounded-md border border-border px-3 py-1.5 text-muted hover:text-text disabled:opacity-50">
            {copy.report.rescan}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-6">
        <ScoreRing score={report.score} size={140} />
        <div className="min-w-0 flex-1">
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-primary">{copy.report.score}</div>
          <h1 className="break-all text-3xl font-bold">{report.project}</h1>
          <p className="mt-1 text-sm text-muted">
            {report.files_scanned} 個檔案{report.languages.length ? `・${report.languages.join("、")}` : ""}・緊急{" "}
            {report.summary.critical}・高 {report.summary.high}・中 {report.summary.medium}・低 {report.summary.low}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {Object.entries(copy.categories).map(([k, label]) => {
          const v = report.category_scores[k];
          const st = covStatus(k);
          const note =
            v == null
              ? AI_CATS.has(k) && st === "skipped" ? copy.report.needsAi : copy.report.notApplicable
              : k === "duplication" && st === "partial" ? copy.report.rulesOnly : null;
          return (
            <div key={k} className="flex flex-col items-center gap-1 rounded-card border border-border bg-surface p-3 text-center">
              <ScoreRing score={v} size={56} label={label} />
              <div className="text-xs">{label}</div>
              {note && <div className="text-[11px] text-muted">{note}</div>}
            </div>
          );
        })}
      </div>

      {expired && (
        <p role="status" className="rounded-card border border-border bg-surface p-4 text-sm text-muted">{copy.report.expired}</p>
      )}

      {!expired && <ImprovePanel report={report} previous={previous} />}

      {critical.length > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-critical/60 bg-surface p-4">
          <p className="text-sm">有 {critical.length} 個緊急問題。可以一次複製全部，貼給 Claude Code 一個一個修。</p>
          <CopyButton text={allCriticalPrompt(context, critical.map((f) => f.fix_prompt))} label={copy.report.allCritical} />
        </div>
      )}

      <div className="flex flex-col gap-3">
        {report.findings.length === 0 && !expired && <p className="text-muted">{copy.report.noFindings}</p>}
        {report.findings.map((f, i) => (
          <FindingCard key={f.fingerprint + i} f={f} advanced={advanced} open={i === 0} context={context} />
        ))}
      </div>

      {repoId && <BadgePanel repoId={repoId} passed={report.summary.critical === 0} />}

      {receipt && <ReceiptPanel receipt={receipt} />}

      <footer className="flex flex-col gap-1 border-t border-border pt-4 text-xs text-muted">
        <p>
          {cost.cost_usd > 0
            ? `${copy.report.cost}：NT$${cost.cost_twd}（US$${cost.cost_usd.toFixed(4)}，${(cost.input_tokens + cost.output_tokens).toLocaleString()} token）`
            : copy.report.free}
        </p>
        <p>{copy.report.keyNote} <Link href="/security" className="text-primary underline-offset-4 hover:underline">{copy.dashboard.security}</Link></p>
        <p>{copy.report.scoreNote}</p>
      </footer>
    </section>
  );
}
