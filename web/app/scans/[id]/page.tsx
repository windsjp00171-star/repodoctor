import { notFound } from "next/navigation";
import { ScanView } from "@/components/ScanView";
import { createClient } from "@/lib/supabase/server";
import type { Finding, ScanRow } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ScanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const supabase = await createClient();
  // RLS：別人的健檢在這裡就是查不到（回 404，不透露它存在）
  const { data: scan } = await supabase.from("scans").select("*, repos(full_name)").eq("id", id).maybeSingle();
  if (!scan) notFound();
  const { data: findings } = scan.status === "done"
    ? await supabase.from("findings").select("*").eq("scan_id", id)
    : { data: [] };
  const { repos, ...row } = scan as ScanRow & { repos: { full_name: string } | null };
  return <ScanView initial={row} repoName={repos?.full_name ?? ""} initialFindings={(findings ?? []) as Finding[]} />;
}
