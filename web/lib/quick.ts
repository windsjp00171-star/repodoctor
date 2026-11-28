// 免登入秒檢：把使用者貼的東西變成 owner/repo，以及把結果轉成報告頁用的形狀。
import type { Finding, Report, Severity } from "./types";

const NAME = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100}$/;

/** 接受 https://github.com/owner/repo（可帶 .git、/tree/...）或 owner/repo；看不懂回 null。 */
export function parseRepoInput(input: string): string | null {
  let s = input.trim();
  s = s.replace(/^(https?:\/\/)?(www\.)?github\.com\//i, "").replace(/^git@github\.com:/i, "");
  const [owner, repo] = s.split(/[/?#]/).filter(Boolean);
  if (!owner || !repo) return null;
  const name = `${owner}/${repo.replace(/\.git$/i, "")}`;
  return NAME.test(name) ? name : null;
}

export interface QuickRow {
  id: string;
  full_name: string;
  status: "queued" | "running" | "done" | "failed";
  score: number | null;
  category_scores: Record<string, number | null> | null;
  summary: Record<Severity, number> | null;
  coverage: Record<string, { status: string; note: string }> | null;
  meta: { project: string; files_scanned: number; languages: string[] } | null;
  findings: Omit<Finding, "id">[] | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

const SEV: Severity[] = ["critical", "high", "medium", "low"];

export function quickToReport(q: QuickRow): Report {
  const findings = (q.findings ?? []).map((f, i) => ({ ...f, id: `${q.id}-${i}` }) as Finding)
    .sort((a, b) => SEV.indexOf(a.severity) - SEV.indexOf(b.severity));
  return {
    project: q.meta?.project ?? q.full_name,
    score: q.score,
    category_scores: q.category_scores ?? {},
    summary: q.summary ?? { critical: 0, high: 0, medium: 0, low: 0 },
    coverage: q.coverage ?? {},
    findings,
    files_scanned: q.meta?.files_scanned ?? 0,
    languages: q.meta?.languages ?? [],
    cost: { input_tokens: 0, output_tokens: 0, cost_usd: 0, cost_twd: 0 },
  };
}
