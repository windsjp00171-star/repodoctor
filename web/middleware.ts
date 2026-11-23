// 登入保護只在這裡統一處理（SPEC CLAUDE.md 規則），頁面裡不各自寫登入檢查。
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PROTECTED = ["/dashboard", "/scans", "/github"];

const REQUIRED_ENV = {
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
};

export async function middleware(request: NextRequest) {
  // 部署時漏設環境變數：講清楚少了哪一個，不要只丟 MIDDLEWARE_INVOCATION_FAILED
  const missing = Object.entries(REQUIRED_ENV).filter(([, v]) => !v).map(([k]) => k);
  if (missing.length) {
    return new NextResponse(
      `網站還沒設定好：少了環境變數 ${missing.join("、")}。\n請在部署平台補上之後重新部署（NEXT_PUBLIC_ 開頭的變數要重新部署才會生效）。`,
      { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }
  let response = NextResponse.next({ request });
  const supabase = createServerClient(REQUIRED_ENV.NEXT_PUBLIC_SUPABASE_URL!, REQUIRED_ENV.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (list) => {
        list.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        list.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });
  // getUser() 會向 Supabase 驗證 token（getSession() 只讀 cookie，不能拿來做保護）
  const { data: { user } } = await supabase.auth.getUser();
  const path = request.nextUrl.pathname;
  if (!user && PROTECTED.some((p) => path === p || path.startsWith(p + "/"))) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(path + request.nextUrl.search)}`;
    return NextResponse.redirect(url);
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|webp)$).*)"],
};
