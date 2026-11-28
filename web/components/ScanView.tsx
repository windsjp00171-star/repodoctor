"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { copy } from "@/lib/copy";
import { RETENTION_DAYS } from "@/lib/legal";
import { motion } from "@/lib/motion";
import { createClient } from "@/lib/supabase/client";
import type { Previous } from "@/lib/improve";
import { type Finding, type ScanRow, toReport } from "@/lib/types";
import { ReportView } from "./ReportView";
import { ScanLive } from "./ScanLive";

export function ScanView({ initial, repoName, initialFindings }: { initial: ScanRow; repoName: string; initialFindings: Finding[] }) {
  const router = useRouter();
  const [scan, setScan] = useState(initial);
  const [findings, setFindings] = useState(initialFindings);
  const [recentFiles, setRecentFiles] = useState<string[]>([]);
  const supabase = useRef(createClient()).current;
  const [previous, setPrevious] = useState<Previous | null>(null);

  // 同一個 repo 上一次完成的健檢，拿來算「修好了哪些」
  useEffect(() => {
    if (scan.status !== "done") return;
    (async () => {
      const { data: prev } = await supabase.from("scans").select("id, score, found, created_at")
        .eq("repo_id", scan.repo_id).eq("status", "done").lt("created_at", scan.created_at)
        .order("created_at", { ascending: false }).limit(1).maybeSingle();
      if (!prev) return;
      const { data: pf } = await supabase.from("findings").select("fingerprint, title, severity").eq("scan_id", prev.id);
      if (prev.found && !pf?.length) return;  // 上一次的細節已過保存期限：沒得比，不要誤報「全部都是新問題」
      setPrevious({ score: prev.score, created_at: prev.created_at, findings: (pf ?? []) as Previous["findings"] });
    })();
  }, [scan.status, scan.repo_id, scan.created_at, supabase]);

  // 掃描進度：Supabase Realtime 推過來（SPEC：真的進度，不是假動畫）。
  // 另外每幾秒補問一次，萬一 Realtime 斷線也不會卡在「掃描中」。
  useEffect(() => {
    if (initial.status === "done" || initial.status === "failed") return;
    const apply = (row: ScanRow) => {
      setScan(row);
      if (row.current_file) setRecentFiles((prev) => [row.current_file!, ...prev.filter((f) => f !== row.current_file)].slice(0, 12));
    };
    const channel = supabase.channel(`scan-${initial.id}`)
      .on("postgres_changes", { event: "UPDATE", schema: "public", table: "scans", filter: `id=eq.${initial.id}` },
        (p) => apply(p.new as ScanRow))
      .subscribe();
    const timer = setInterval(async () => {
      const { data } = await supabase.from("scans").select("*").eq("id", initial.id).single();  // 補問：Realtime 斷線時的保險
      if (data) apply(data as ScanRow);
    }, motion.pollMs * 5);
    return () => { clearInterval(timer); supabase.removeChannel(channel); };
  }, [initial.id, initial.status, supabase]);

  // 完成時抓 findings
  useEffect(() => {
    if (scan.status !== "done" || findings.length || !scan.found) return;
    supabase.from("findings").select("*").eq("scan_id", scan.id).then(({ data }) => data && setFindings(data as Finding[]));
  }, [scan.status, scan.found, scan.id, findings.length, supabase]);

  async function rescan() {
    const { data } = await supabase.from("scans").insert({ repo_id: scan.repo_id, use_ai: scan.use_ai }).select("id").single();
    if (data) router.push(`/scans/${data.id}`);
  }

  // 細節過了保存期限被 worker 刪掉：照樣顯示分數，並說明原因（不要卡在「掃描中」）
  const expired = scan.status === "done" && !!scan.found && !findings.length && !!scan.finished_at
    && Date.now() - new Date(scan.finished_at).getTime() > RETENTION_DAYS * 86_400_000;
  if (scan.status === "done" && (findings.length || !scan.found || expired))
    return <ReportView report={toReport(scan, findings)} previous={previous} onRescan={rescan} expired={expired} repoId={scan.repo_id}
      receipt={{ mode: "app", startedAt: scan.started_at ?? null, finishedAt: scan.finished_at, calls: scan.token_usage?.calls ?? [] }} />;
  if (scan.status === "failed")
    return (
      <section className="flex flex-col gap-3">
        <h1 className="text-2xl font-bold text-critical">{copy.scanning.failed}</h1>
        <p>{scan.error ?? copy.errors.workerFailed}</p>
        <Link href="/dashboard" className="text-primary">← {copy.report.back}</Link>
      </section>
    );
  return <ScanLive project={repoName} scan={scan} recentFiles={recentFiles} />;
}
