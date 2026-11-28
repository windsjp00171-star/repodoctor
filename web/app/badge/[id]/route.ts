// 公開的健檢徽章（沒登入也看得到，GitHub README 會來抓）。
// 只透過資料庫的 badge_status() 拿分數與「有沒有緊急問題」，讀不到任何問題內容或 repo 名稱。
import { badgeSvg, type BadgeStatus } from "@/lib/badge";
import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const id = (await params).id.replace(/\.svg$/, "");
  let status: BadgeStatus = null;
  if (UUID.test(id)) {
    const supabase = await createClient();
    const { data } = await supabase.rpc("badge_status", { badge_id: id });
    status = (Array.isArray(data) ? data[0] : data) ?? null;
  }
  return new Response(badgeSvg(status), {
    headers: { "Content-Type": "image/svg+xml; charset=utf-8", "Cache-Control": "public, max-age=300" },
  });
}
