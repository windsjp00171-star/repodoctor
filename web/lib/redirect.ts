// 只接受站內路徑。光擋 "//" 不夠：瀏覽器把 "/\\evil.com" 當成 "//evil.com"，會被導去別的網站。
// 所以實際組出網址，確認沒有離開本站。
export function safeNext(n: string | null, origin: string): string {
  if (!n || !n.startsWith("/") || n.includes("\\")) return "/dashboard";
  try {
    const u = new URL(n, origin);
    return u.origin === origin ? u.pathname + u.search + u.hash : "/dashboard";
  } catch {
    return "/dashboard";
  }
}
