"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { copy } from "@/lib/copy";
import { createClient } from "@/lib/supabase/client";
import type { Repo } from "@/lib/types";
import { ScoreRing } from "./ScoreRing";

export function RepoList({ repos, aiEnabled }: { repos: Repo[]; aiEnabled: boolean }) {
  const router = useRouter();
  const [ai, setAi] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start(repoId: string) {
    setBusy(repoId);
    setError(null);
    // RLS 保證只能對自己的 repo 發起；status、分數等欄位使用者寫不了
    const { data, error: err } = await createClient().from("scans").insert({ repo_id: repoId, use_ai: ai && aiEnabled }).select("id").single();
    if (err || !data) {
      setError(copy.errors.startFailed);
      setBusy(null);
      return;
    }
    router.push(`/scans/${data.id}`);
  }

  return (
    <section className="flex flex-col gap-4">
      <label className={`flex items-center gap-2 text-sm ${aiEnabled ? "" : "text-muted"}`}>
        <input id="use-ai" type="checkbox" className="h-4 w-4 accent-[rgb(var(--primary))]" checked={ai} disabled={!aiEnabled}
          onChange={(e) => setAi(e.target.checked)} />
        {copy.ai.label}
        <span className="text-muted">— {aiEnabled ? copy.ai.hint : copy.ai.noKey}</span>
      </label>
      {error && <p role="alert" className="rounded-card border border-critical px-4 py-3 text-sm text-critical">{error}</p>}
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {repos.map((r) => {
          const last = r.last_scan;
          return (
            <li key={r.id} className="flex items-center gap-3 rounded-card border border-border bg-surface p-4">
              <ScoreRing score={last?.status === "done" ? last.score : null} size={56} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold" title={r.full_name}>{r.full_name}</div>
                <div className="truncate text-xs text-muted">
                  {!last ? copy.projects.never
                    : last.status === "done" ? `${copy.projects.lastScan} ${new Date(last.created_at).toLocaleString("zh-TW", { dateStyle: "short", timeStyle: "short" })}`
                    : copy.dashboard[last.status]}
                  {last?.status === "done" && last.summary && last.summary.critical > 0 && (
                    <span className="ml-2 font-semibold text-critical">緊急 {last.summary.critical}</span>
                  )}
                </div>
                <div className="mt-2 flex gap-2">
                  <button type="button" onClick={() => start(r.id)} disabled={busy !== null}
                    className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-bg transition hover:brightness-110 disabled:opacity-50">
                    {busy === r.id ? "啟動中…" : copy.projects.start}
                  </button>
                  {last && (
                    <Link href={`/scans/${last.id}`} className="rounded-md border border-border px-3 py-1.5 text-xs text-muted hover:text-text">
                      {copy.projects.view}
                    </Link>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
