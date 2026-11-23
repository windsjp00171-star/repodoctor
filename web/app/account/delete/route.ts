// 刪除使用者在 RepoDoctor 的所有資料，連帳號（含 email）一起刪。
// 1. 先刪 installations：repos → scans → findings 都是 on delete cascade，馬上看不到。
// 2. 標記 profiles.delete_requested_at：worker 用 secret key 刪掉 auth 帳號（網站沒有、也不該有那把鑰匙）。
//    資料庫 trigger 會順便叫醒 worker，通常幾分鐘內完成（supabase/migrations/003）。
// 3. 登出，回首頁。
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(new URL("/login", request.url), { status: 303 });
  const { error: e1 } = await supabase.from("installations").delete().eq("user_id", user.id);
  const { error: e2 } = e1 ? { error: e1 }
    : await supabase.from("profiles").update({ delete_requested_at: new Date().toISOString() }).eq("id", user.id);
  if (e2) return NextResponse.redirect(new URL("/dashboard?delete_error=1", request.url), { status: 303 });
  await supabase.auth.signOut();
  return NextResponse.redirect(new URL("/?account_deleted=1", request.url), { status: 303 });
}
