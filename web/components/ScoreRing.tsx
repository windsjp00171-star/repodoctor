"use client";
import { useEffect, useState } from "react";
import { motion } from "@/lib/motion";

const colorFor = (s: number | null) =>
  s == null ? "rgb(var(--text-muted))" : s < 60 ? "rgb(var(--critical))" : s < 80 ? "rgb(var(--high))" : "rgb(var(--healthy))";

/** 健康分數環：從 0 跑到分數，數字同步跳動（SPEC 標誌時刻 2）。 */
export function ScoreRing({ score, size = 120, label }: { score: number | null; size?: number; label?: string }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (score == null) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return setShown(score);
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / motion.scoreRingMs);
      setShown(Math.round(score * (1 - Math.pow(1 - k, 3))));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [score]);
  const stroke = Math.max(4, size / 16);
  const r = size / 2 - stroke;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${label ?? "健康分數"} ${score ?? "—"}`} className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(var(--border))" strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={colorFor(score == null ? null : shown)} strokeWidth={stroke}
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - shown / 100)} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="font-num font-bold" fontSize={size * 0.3} fill="rgb(var(--text))">
        {score == null ? "—" : shown}
      </text>
    </svg>
  );
}
