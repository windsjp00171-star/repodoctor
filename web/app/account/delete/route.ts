// 刪除使用者在 RepoDoctor 的所有資料。
// 只刪 installations：repos → scans → findings 都是 on delete cascade，一起刪掉。
// 用的是使用者自己的登入（RLS：只能刪自己的），不是 secret key。
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(new URL("/login", request.url), { status: 303 });
  const { error } = await supabase.from("installations").delete().eq("user_id", user.id);
  const url = new URL("/dashboard", request.url);
  url.searchParams.set(error ? "delete_error" : "deleted", "1");
  return NextResponse.redirect(url, { status: 303 });
}
