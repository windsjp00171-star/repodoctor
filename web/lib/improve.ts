// 「幫你改善」的計算：和上一次健檢比較、挑出最該加強的類別。純函式，方便測試。
import { copy } from "./copy";
import type { Finding, Report, Severity } from "./types";

export interface Previous {
  score: number | null;
  created_at: string;
  findings: Pick<Finding, "fingerprint" | "title" | "severity">[];
}

export interface Progress {
  scoreDelta: number | null;
  fixed: { title: string; severity: Severity }[];
  added: { title: string; severity: Severity }[];
  remaining: number;
}

/** 用 fingerprint 比對（不含行號，改了別的程式也比得起來）。 */
export function compare(prev: Previous, report: Report): Progress {
  const now = new Set(report.findings.map((f) => f.fingerprint));
  const before = new Set(prev.findings.map((f) => f.fingerprint));
  return {
    scoreDelta: prev.score != null && report.score != null ? report.score - prev.score : null,
    fixed: prev.findings.filter((f) => !now.has(f.fingerprint)).map(({ title, severity }) => ({ title, severity })),
    added: report.findings.filter((f) => !before.has(f.fingerprint)).map(({ title, severity }) => ({ title, severity })),
    remaining: report.findings.filter((f) => before.has(f.fingerprint)).length,
  };
}

/** 分數最低、而且有問題的類別，最多兩個。沒檢查的類別（null）不算。 */
export function weakest(report: Report, max = 2): string[] {
  return Object.entries(report.category_scores)
    .filter(([k, v]) => v != null && v < 100 && copy.improve.directions[k])
    .sort((a, b) => (a[1] as number) - (b[1] as number))
    .slice(0, max)
    .map(([k]) => k);
}

export function claudeMdRules(categories: string[]): string {
  return [copy.improve.rulesHeader, ...categories.map((c) => copy.improve.directions[c].rule)].join("\n");
}
