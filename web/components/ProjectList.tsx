"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { copy } from "@/lib/copy";
import type { ScanSummary } from "@/lib/types";
import { ScoreRing } from "./ScoreRing";

type Project = { name: string; path: string; last: ScanSummary | null };

export function ProjectList({ projects, aiAvailable }: { projects: Project[]; aiAvailable: boolean }) {
  const router = useRouter();
  const [ai, setAi] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [custom, setCustom] = useState("");

  async function start(path: string) {
    setBusy(path);
    setError(null);
    const res = await fetch("/api/scans", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path, ai }) });
    const data = await res.json().catch(() => ({ success: false, error: copy.errors.workerFailed }));
    if (!data.success) {
      setError(data.error);
      setBusy(null);
      return;
    }
    router.push(`/scans/${data.id}`);
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-xl font-bold">{copy.projects.title}</h2>
        <label className={`flex items-center gap-2 text-sm ${aiAvailable ? "" : "text-muted"}`}>
          <input id="use-ai" type="checkbox" className="h-4 w-4 accent-[rgb(var(--primary))]" checked={ai} disabled={!aiAvailable}
            onChange={(e) => setAi(e.target.checked)} />
          {copy.ai.label}
        </label>
      </div>
      <p className="text-sm text-muted">{aiAvailable ? copy.ai.hint : copy.ai.noKey}</p>
      {error && <p role="alert" className="rounded-card border border-critical px-4 py-3 text-sm text-critical">{error}</p>}

      {projects.length === 0 && <p className="text-muted">{copy.projects.empty}</p>}
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((p) => (
          <li key={p.path} className="flex items-center gap-3 rounded-card border border-border bg-surface p-4">
            <ScoreRing score={p.last?.score ?? null} size={56} />
            <div className="min-w-0 flex-1">
              <div className="truncate font-semibold" title={p.name}>{p.name}</div>
              <div className="truncate text-xs text-muted">
                {p.last ? `${copy.projects.lastScan} ${new Date(p.last.started_at).toLocaleString("zh-TW", { dateStyle: "short", timeStyle: "short" })}` : copy.projects.never}
                {p.last?.summary && p.last.summary.critical > 0 && <span className="ml-2 font-semibold text-critical">緊急 {p.last.summary.critical}</span>}
              </div>
              <div className="mt-2 flex gap-2">
                <button type="button" onClick={() => start(p.path)} disabled={busy !== null}
                  className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-bg transition hover:brightness-110 disabled:opacity-50">
                  {busy === p.path ? "啟動中…" : copy.projects.start}
                </button>
                {p.last?.status === "done" && (
                  <Link href={`/scans/${p.last.id}`} className="rounded-md border border-border px-3 py-1.5 text-xs text-muted hover:text-text">
                    {copy.projects.view}
                  </Link>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <form className="flex flex-col gap-2 sm:flex-row" onSubmit={(e) => { e.preventDefault(); if (custom.trim()) start(custom.trim()); }}>
        <label htmlFor="custom-path" className="sr-only">{copy.projects.custom}</label>
        <input id="custom-path" value={custom} onChange={(e) => setCustom(e.target.value)} placeholder={copy.projects.customPlaceholder}
          className="min-w-0 flex-1 rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm placeholder:text-muted" />
        <button type="submit" disabled={busy !== null || !custom.trim()}
          className="rounded-md border border-primary px-4 py-2 text-sm font-semibold text-primary disabled:opacity-50">
          {copy.projects.custom}：{copy.projects.start}
        </button>
      </form>
    </section>
  );
}
