// 動畫參數集中在這裡，全站共用同一組節奏（SPEC CLAUDE.md 規則）。
import type { CSSProperties } from "react";
export const motion = {
  scoreRingMs: 1200, // 分數環從 0 跑到分數
  scanCycleS: 2.4, // 掃描光一個來回
  pulseS: 2.2, // 緊急卡片邊框光暈
  pollMs: 600, // 掃描中多久問一次進度
  copiedMs: 1600, // 「已複製」停留多久
} as const;

export const motionCssVars = {
  "--motion-scan": `${motion.scanCycleS}s`,
  "--motion-pulse": `${motion.pulseS}s`,
} as CSSProperties;
