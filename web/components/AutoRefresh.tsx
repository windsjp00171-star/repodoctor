"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** 等 GitHub 安裝確認時，自己重新整理，使用者不用一直按 F5。最多等 10 分鐘。 */
export function AutoRefresh({ everyMs = 4000, maxMs = 600_000 }: { everyMs?: number; maxMs?: number }) {
  const router = useRouter();
  useEffect(() => {
    const started = Date.now();
    const t = setInterval(() => {
      if (Date.now() - started > maxMs) return clearInterval(t);
      router.refresh();
    }, everyMs);
    return () => clearInterval(t);
  }, [router, everyMs, maxMs]);
  return null;
}
