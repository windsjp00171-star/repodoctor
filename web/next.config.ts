import type { NextConfig } from "next";

// 全站的安全標頭。
// - 不准別的網站把我們放進 iframe（擋「把刪除按鈕藏在別的畫面下面騙你點」這類點擊劫持）
// - 不讓瀏覽器猜檔案類型、跨站時不帶完整網址、關掉用不到的裝置權限
// HTTPS 的 HSTS 由 Vercel 自動加。
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://github.com" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
];

const config: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default config;
