"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { copy } from "@/lib/copy";
import { motion } from "@/lib/motion";
import type { ScanStatus } from "@/lib/types";
import { ReportView } from "./ReportView";
import { ScanLive } from "./ScanLive";

export function ScanView({ initial }: { initial: ScanStatus }) {
  const [scan, setScan] = useState(initial);
  useEffect(() => {
    if (scan.status !== "running") return;
    const t = setTimeout(async () => {
      const res = await fetch(`/api/scans/${scan.meta.id}`, { cache: "no-store" }).catch(() => null);
      const data = await res?.json().catch(() => null);
      setScan(data?.success ? data.scan : { ...scan }); // 網路抖一下就再問一次
    }, motion.pollMs);
    return () => clearTimeout(t);
  }, [scan]);

  if (scan.status === "done" && scan.report) return <ReportView scan={scan} report={scan.report} />;
  if (scan.status === "failed")
    return (
      <section className="flex flex-col gap-3">
        <h1 className="text-2xl font-bold text-critical">
          {copy.scanning.failed}：{scan.meta.project}
        </h1>
        <p className="text-muted">{copy.errors.workerFailed}</p>
        {scan.error && (
          <pre className="overflow-x-auto rounded-card border border-border bg-surface p-3 font-mono text-xs">{scan.error}</pre>
        )}
        <Link href="/" className="text-primary">← {copy.report.back}</Link>
      </section>
    );
  return <ScanLive scan={scan} />;
}
