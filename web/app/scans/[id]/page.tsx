import { notFound } from "next/navigation";
import { ScanView } from "@/components/ScanView";
import { createClient } from "@/lib/supabase/server";
import type { Finding, ScanRow } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ScanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const supabase = await createClient();
  // scans 和 repos 之間有兩條外鍵（scans.repo_id、repos.last_scan_id），一定要指定走 repo_id，
  // 不然 PostgREST 會回「關聯不明確」的錯誤。
  // RLS：別人的健檢在這裡就是查不到（回 404，不透露它存在）；真的出錯就丟出來，不要假裝成 404。
  const { data: scan, error } = await supabase.from("scans").select("*, repos!repo_id(full_name)").eq("id", id).maybeSingle();
  if (error) throw new Error(`讀取健檢失敗：${error.message}`);
  if (!scan) notFound();
  const { data: findings, error: fErr } = scan.status === "done"
    ? await supabase.from("findings").select("*").eq("scan_id", id)
    : { data: [], error: null };
  if (fErr) throw new Error(`讀取健檢結果失敗：${fErr.message}`);
  const { repos, ...row } = scan as ScanRow & { repos: { full_name: string } | null };
  return <ScanView initial={row} repoName={repos?.full_name ?? ""} initialFindings={(findings ?? []) as Finding[]} />;
}
