// 使用者在 GitHub 裝完 App 後，GitHub 帶著 installation_id 導回這裡（GitHub App 的 Setup URL）。
// 這裡只記下「這個人說他裝了 installation X」（狀態 pending）。
// 「這個安裝真的是他的嗎」由 worker 向 GitHub 確認——網址上的參數任何人都能偽造。
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const id = Number(url.searchParams.get("installation_id"));
  if (Number.isSafeInteger(id) && id > 0) {
    const supabase = await createClient();
    // 重複安裝（同一個 id）會撞 unique，忽略即可
    await supabase.from("installations").insert({ github_installation_id: id });
  }
  return NextResponse.redirect(new URL("/dashboard", url.origin));
}
