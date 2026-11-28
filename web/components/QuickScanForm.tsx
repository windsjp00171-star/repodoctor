"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { copy } from "@/lib/copy";
import { parseRepoInput } from "@/lib/quick";
import { createClient } from "@/lib/supabase/client";

/** 首頁的免登入秒檢：貼上公開 repo 網址就開始，不用登入。 */
export function QuickScanForm() {
  const q = copy.quick;
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const name = parseRepoInput(value);
    if (!name) return setError(q.invalid);
    setBusy(true);
    setError(null);
    const { data, error } = await createClient().rpc("request_quick_scan", { repo: name });
    if (error || !data) {
      setBusy(false);
      return setError(/daily_limit/.test(error?.message ?? "") ? q.dailyLimit : q.failed);
    }
    router.push(`/quick/${data}`);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2 rounded-card border border-border bg-surface p-4">
      <label htmlFor="quick-repo" className="font-semibold">{q.label}</label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input id="quick-repo" value={value} onChange={(e) => setValue(e.target.value)} inputMode="url" autoComplete="off"
          placeholder={q.placeholder}
          className="min-w-0 flex-1 rounded-md border border-border bg-bg px-3 py-2.5 font-mono text-sm outline-none focus:border-primary" />
        <button disabled={busy}
          className="rounded-md bg-primary px-5 py-2.5 font-semibold text-bg transition hover:brightness-110 disabled:opacity-60">
          {busy ? q.sending : q.button}
        </button>
      </div>
      {error ? <p role="alert" className="text-sm text-critical">{error}</p> : <p className="text-xs text-muted">{q.note}</p>}
    </form>
  );
}
