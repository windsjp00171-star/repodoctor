"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { copy } from "@/lib/copy";
import { demoPrevious, demoReceipt, demoReport } from "@/lib/demo";
import { ReportView } from "./ReportView";

/** 範例報告：跟登入後的報告頁是同一個元件，只是資料是假的；「重新健檢」帶去登入。 */
export function DemoReport() {
  const router = useRouter();
  const d = copy.demo;
  return (
    <>
      <div role="note" className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-primary/60 bg-surface p-4 text-sm">
        <p><span className="font-semibold text-primary">{d.badge}</span>　{d.note}</p>
        <Link href="/login" className="rounded-md bg-primary px-4 py-2 font-semibold text-bg transition hover:brightness-110">{d.cta}</Link>
      </div>
      <ReportView report={demoReport} previous={demoPrevious} onRescan={async () => router.push("/login")} receipt={demoReceipt} />
    </>
  );
}
