"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { copy } from "@/lib/copy";
import { type QuickRow, quickToReport } from "@/lib/quick";
import { createClient } from "@/lib/supabase/client";
import { ReportView } from "./ReportView";

/** 秒檢結果：沒登入也看得到，所以用輪詢（Realtime 需要登入）。 */
export function QuickScanView({ id }: { id: string }) {
  const q = copy.quick;
  const router = useRouter();
  const supabase = useRef(createClient()).current;
  const [row, setRow] = useState<QuickRow | null | undefined>(undefined);

  useEffect(() => {
    let stop = false;
    async function poll() {
      const { data } = await supabase.rpc("quick_scan_status", { scan_id: id });
      const r = (Array.isArray(data) ? data[0] : data) as QuickRow | undefined;
      if (stop) return;
      setRow(r ?? null);
      if (r && (r.status === "queued" || r.status === "running")) setTimeout(poll, 3000);
    }
    poll();
    return () => { stop = true; };
  }, [id, supabase]);

  async function rescan() {
    if (!row) return;
    const { data } = await supabase.rpc("request_quick_scan", { repo: row.full_name });
    if (data) router.push(`/quick/${data}`);
  }

  if (row === undefined) return <p className="text-muted">…</p>;
  if (row === null)
    return (
      <section className="flex flex-col gap-3">
        <h1 className="text-2xl font-bold">{q.notFound}</h1>
        <Link href="/" className="text-primary">← {copy.security.back.replace("← ", "")}</Link>
      </section>
    );
  if (row.status === "failed")
    return (
      <section className="flex flex-col gap-3">
        <h1 className="text-2xl font-bold text-critical">{q.failedTitle}</h1>
        <p>{row.error}</p>
        <Link href="/" className="text-primary">{q.tryAnother}</Link>
      </section>
    );
  if (row.status !== "done")
    return (
      <section className="flex flex-col gap-4">
        <div className="font-mono text-xs uppercase tracking-[0.14em] text-primary">{copy.scanning.title}</div>
        <h1 className="break-all text-2xl font-bold">{row.full_name}</h1>
        <p className="flex items-center gap-3 rounded-card border border-primary/50 bg-surface p-4 text-sm">
          <span aria-hidden className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
          {row.status === "queued" ? q.queued : q.running}
        </p>
      </section>
    );

  return (
    <>
      <div role="note" className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-primary/60 bg-surface p-4 text-sm">
        <p><span className="font-semibold text-primary">{q.badge}</span>　{q.upsell}</p>
        <Link href="/login" className="rounded-md bg-primary px-4 py-2 font-semibold text-bg transition hover:brightness-110">{q.upsellCta}</Link>
      </div>
      <ReportView report={quickToReport(row)} previous={null} onRescan={rescan} />
    </>
  );
}
