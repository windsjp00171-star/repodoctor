// 瀏覽器端 Supabase client。全站只在這裡建立（SPEC CLAUDE.md 規則）。
// 只用公開的 anon key；service role key 絕不能出現在前端。
import { createBrowserClient } from "@supabase/ssr";

export const createClient = () =>
  createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
