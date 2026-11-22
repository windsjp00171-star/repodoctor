// 伺服器端 Supabase client（Server Component、Route Handler 用）。全站只在這裡建立。
// 一樣只用 anon key ＋ 使用者自己的登入 cookie，所以資料庫的 RLS 照樣生效。
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const store = await cookies();
  return createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    cookies: {
      getAll: () => store.getAll(),
      setAll: (list) => {
        try {
          list.forEach(({ name, value, options }) => store.set(name, value, options));
        } catch {
          /* Server Component 裡不能寫 cookie；middleware 會負責更新 session */
        }
      },
    },
  });
}
