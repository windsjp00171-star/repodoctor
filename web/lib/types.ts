// 對應 supabase/migrations/001_init.sql 的資料表。

export type Severity = "critical" | "high" | "medium" | "low";

export interface Finding {
  id: string;
  category: string;
  severity: Severity;
  title: string;
  plain_explanation: string;
  advanced_explanation: string;
  fix_prompt: string;
  file_path: string | null;
  line: number | null;
  masked_snippet: string | null;
  source: "rule" | "ai";
  fingerprint: string;
}

export interface ScanRow {
  id: string;
  repo_id: string;
  use_ai: boolean;
  status: "queued" | "running" | "done" | "failed";
  progress: number;
  stage: string | null;
  current_file: string | null;
  found: number;
  score: number | null;
  category_scores: Record<string, number | null> | null;
  summary: Record<Severity, number> | null;
  coverage: Record<string, { status: string; note: string }> | null;
  meta: { project: string; files_scanned: number; languages: string[] } | null;
  token_usage: { total: { input_tokens: number; output_tokens: number; cost_usd: number; cost_twd: number } } | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface Repo {
  id: string;
  full_name: string;
  language: string | null;
  last_scan: Pick<ScanRow, "id" | "status" | "score" | "summary" | "created_at"> | null;
}

/** 報告頁用的形狀：一筆 scans ＋ 它的 findings。 */
export interface Report {
  project: string;
  score: number | null;
  category_scores: Record<string, number | null>;
  summary: Record<Severity, number>;
  coverage: Record<string, { status: string; note: string }>;
  findings: Finding[];
  files_scanned: number;
  languages: string[];
  cost: { input_tokens: number; output_tokens: number; cost_usd: number; cost_twd: number };
}

const SEV_ORDER: Severity[] = ["critical", "high", "medium", "low"];

export function toReport(scan: ScanRow, findings: Finding[]): Report {
  return {
    project: scan.meta?.project ?? "",
    score: scan.score,
    category_scores: scan.category_scores ?? {},
    summary: scan.summary ?? { critical: 0, high: 0, medium: 0, low: 0 },
    coverage: scan.coverage ?? {},
    findings: [...findings].sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity)),
    files_scanned: scan.meta?.files_scanned ?? 0,
    languages: scan.meta?.languages ?? [],
    cost: scan.token_usage?.total ?? { input_tokens: 0, output_tokens: 0, cost_usd: 0, cost_twd: 0 },
  };
}
