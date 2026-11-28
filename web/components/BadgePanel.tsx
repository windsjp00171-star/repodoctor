"use client";
import { useEffect, useRef, useState } from "react";
import { copy } from "@/lib/copy";
import { createClient } from "@/lib/supabase/client";
import { CopyButton } from "./CopyButton";

/** 讓使用者「自己選擇」公開這個 repo 的健檢徽章。徽章只顯示分數，不顯示任何問題。 */
export function BadgePanel({ repoId, passed }: { repoId: string; passed: boolean }) {
  const b = copy.badge;
  const supabase = useRef(createClient()).current;
  const [id, setId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    supabase.from("badges").select("id").eq("repo_id", repoId).maybeSingle()
      .then(({ data }) => data && setId(data.id));
  }, [repoId, supabase]);

  async function create() {
    setBusy(true);
    setError(false);
    const { data, error } = await supabase.from("badges").insert({ repo_id: repoId }).select("id").single();
    setBusy(false);
    if (error) return setError(true);
    setId(data.id);
  }
  async function remove() {
    if (!id) return;
    await supabase.from("badges").delete().eq("id", id);
    setId(null);
  }

  const origin = typeof window === "undefined" ? "" : window.location.origin;
  const md = id ? `[![RepoDoctor](${origin}/badge/${id}.svg)](${origin}/?ref=badge)` : "";

  return (
    <section className="flex flex-col gap-3 rounded-card border border-border bg-surface p-5">
      <h2 className="font-bold">{b.title}</h2>
      <p className="text-sm leading-relaxed text-muted">{passed ? b.bodyPassed : b.bodyNotYet}</p>
      {!id ? (
        <div>
          <button type="button" onClick={create} disabled={busy}
            className="rounded-md border border-primary px-4 py-2 text-sm font-semibold text-primary transition hover:bg-primary/10 disabled:opacity-50">
            {b.create}
          </button>
          {error && <p role="alert" className="mt-2 text-sm text-critical">{b.failed}</p>}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`/badge/${id}.svg`} alt="RepoDoctor" className="self-start" />
          <div className="flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap rounded bg-bg px-2 py-1.5 font-mono text-xs">{md}</code>
            <CopyButton text={md} label={b.copy} />
          </div>
          <p className="text-xs text-muted">{b.howto}</p>
          <button type="button" onClick={remove} className="self-start text-xs text-muted underline-offset-4 hover:text-text hover:underline">
            {b.remove}
          </button>
        </div>
      )}
    </section>
  );
}
