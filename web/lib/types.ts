// 對應 worker 輸出的 JSON 報告（worker/scanner/report.py）。

export type Severity = "critical" | "high" | "medium" | "low";

export interface Finding {
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

export interface Report {
  project: string;
  score: number | null;
  category_scores: Record<string, number | null>;
  summary: Record<Severity, number>;
  coverage: Record<string, { status: string; note: string }>;
  findings: Finding[];
  files_scanned: number;
  languages: string[];
  token_usage: { estimated: boolean; total: { input_tokens: number; output_tokens: number; cost_usd: number; cost_twd: number } };
}

export interface ScanStatus {
  meta: { id: string; project: string; path: string; ai: boolean; started_at: string };
  status: "running" | "done" | "failed";
  progress: { progress: number; stage: string; current_file: string | null; found: number };
  recentFiles: string[];
  report: Report | null;
  error: string | null;
}

export interface ScanSummary {
  id: string;
  project: string;
  path: string;
  started_at: string;
  status: ScanStatus["status"];
  score: number | null;
  summary: Record<Severity, number> | null;
}
