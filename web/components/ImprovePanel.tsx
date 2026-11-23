"use client";
import { copy } from "@/lib/copy";
import { claudeMdRules, compare, type Previous, weakest } from "@/lib/improve";
import type { Report } from "@/lib/types";
import { CopyButton } from "./CopyButton";

const SEV_ICON: Record<string, string> = { critical: "▲", high: "●", medium: "◆", low: "○" };

/** 報告頁上方：上次以來的進步 ＋ 接下來怎麼做 ＋ 改善方向。 */
export function ImprovePanel({ report, previous }: { report: Report; previous: Previous | null }) {
  const im = copy.improve;
  const p = previous ? compare(previous, report) : null;
  const s = report.summary;
  const next = s.critical ? im.nextCritical(s.critical) : s.high ? im.nextHigh(s.high) : report.findings.length ? im.nextRest : im.nextClean;
  const cats = weakest(report);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="flex flex-col gap-3 rounded-card border border-border bg-surface p-5">
        <h2 className="font-bold">{im.progressTitle}</h2>
        {!p ? (
          <p className="text-sm text-muted">{im.progressNone}</p>
        ) : (
          <>
            <p className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              {p.scoreDelta != null && (
                <span className={`font-num text-2xl font-bold ${p.scoreDelta > 0 ? "text-healthy" : p.scoreDelta < 0 ? "text-critical" : "text-muted"}`}>
                  {p.scoreDelta > 0 ? "+" : ""}{p.scoreDelta} 分
                </span>
              )}
              <span className="text-sm">
                <span className="text-healthy">{im.fixed} {p.fixed.length}</span>・
                <span className={p.added.length ? "text-high" : ""}>{im.added} {p.added.length}</span>・
                {im.remaining} {p.remaining}
              </span>
            </p>
            {p.fixed.length > 0 && (
              <ul className="flex flex-col gap-1 text-sm">
                {p.fixed.slice(0, 6).map((f, i) => (
                  <li key={i} className="text-muted"><span className="text-healthy">✓</span> <s>{f.title}</s></li>
                ))}
              </ul>
            )}
            {p.added.length > 0 && (
              <ul className="flex flex-col gap-1 text-sm">
                {p.added.slice(0, 6).map((f, i) => (
                  <li key={i}><span className="text-high">{SEV_ICON[f.severity]}</span> {f.title}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <section className="flex flex-col gap-2 rounded-card border border-border bg-surface p-5">
        <h2 className="font-bold">{im.nextTitle}</h2>
        <ol className="flex list-decimal flex-col gap-1 pl-5 text-sm leading-relaxed">
          <li>{next}</li>
          {report.findings.length > 0 && <li>{im.nextRescan}</li>}
          {cats.length > 0 && <li>{im.directionSub}</li>}
        </ol>
      </section>

      {cats.length > 0 && (
        <section className="flex flex-col gap-4 rounded-card border border-primary/40 bg-surface p-5 lg:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-bold">{im.directionTitle}</h2>
              <p className="mt-1 text-sm text-muted">{im.directionSub}</p>
            </div>
            <CopyButton text={claudeMdRules(cats)} label={im.copyRules} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {cats.map((c) => {
              const d = im.directions[c];
              return (
                <div key={c} className="flex flex-col gap-1 rounded-card border border-border bg-bg p-4">
                  <span className="text-xs text-muted">{copy.categories[c]}・{report.category_scores[c]} 分</span>
                  <span className="font-semibold">{d.goal}</span>
                  <span className="text-sm text-muted">{d.why}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
