// 伺服器端：建立健檢、啟動 Python worker、讀取進度與報告。
//
// Phase 0.5 先在本機跑：結果存在 web/data/scans/<id>/。
// 欄位對齊 SPEC 的 scans 表（status、progress、current_file、score、token_usage…），
// 之後換成 Supabase 時只要換掉這個檔案，頁面不用動。
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import type { Report, ScanStatus, ScanSummary } from "./types";

const WEB_ROOT = process.cwd();
const DATA_DIR = path.join(WEB_ROOT, "data", "scans");
const WORKER_DIR = process.env.WORKER_DIR ?? path.resolve(WEB_ROOT, "..", "worker");
const PYTHON = process.env.PYTHON ?? "python3";
export const PROJECTS_ROOT = process.env.PROJECTS_ROOT ?? path.resolve(WEB_ROOT, "..", "..");

export const aiAvailable = () => Boolean(process.env.ANTHROPIC_API_KEY);

const dir = (id: string) => {
  if (!/^[0-9a-f-]{36}$/.test(id)) throw new Error("bad id");
  return path.join(DATA_DIR, id);
};
const readJson = <T>(p: string): T | null => {
  try {
    return JSON.parse(fs.readFileSync(p, "utf8")) as T;
  } catch {
    return null;
  }
};

export function listProjects(): { name: string; path: string }[] {
  try {
    return fs
      .readdirSync(PROJECTS_ROOT, { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith("."))
      .map((d) => ({ name: d.name, path: path.join(PROJECTS_ROOT, d.name) }))
      .filter((p) => fs.existsSync(path.join(p.path, ".git")))
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    return [];
  }
}

export function startScan(projectPath: string, useAi: boolean): string {
  const abs = path.resolve(projectPath);
  if (!fs.existsSync(abs) || !fs.statSync(abs).isDirectory()) throw new Error("badPath");
  const id = randomUUID();
  const d = dir(id);
  fs.mkdirSync(d, { recursive: true });
  const meta = { id, project: path.basename(abs), path: abs, ai: useAi && aiAvailable(), started_at: new Date().toISOString() };
  fs.writeFileSync(path.join(d, "meta.json"), JSON.stringify(meta));

  const args = ["-m", "cli", abs, "-q", "-o", path.join(d, "report.json"), "--progress-file", path.join(d, "progress.jsonl")];
  if (!meta.ai) args.push("--no-ai");
  const log = fs.openSync(path.join(d, "worker.log"), "a");
  const child = spawn(PYTHON, args, { cwd: WORKER_DIR, stdio: ["ignore", log, log], detached: true });
  child.on("exit", (code) => fs.writeFileSync(path.join(d, "exit.json"), JSON.stringify({ code })));
  child.unref();
  return id;
}

export function getScan(id: string): ScanStatus | null {
  const d = dir(id);
  const meta = readJson<ScanStatus["meta"]>(path.join(d, "meta.json"));
  if (!meta) return null;
  const report = readJson<Report>(path.join(d, "report.json"));
  const exit = readJson<{ code: number }>(path.join(d, "exit.json"));
  let progress: ScanStatus["progress"] = { progress: 0, stage: "準備中", current_file: null, found: 0 };
  const recentFiles: string[] = [];
  try {
    const lines = fs.readFileSync(path.join(d, "progress.jsonl"), "utf8").trim().split("\n").filter(Boolean);
    if (lines.length) progress = JSON.parse(lines[lines.length - 1]);
    for (const l of lines.slice(-40).reverse()) {
      const f = JSON.parse(l).current_file;
      if (f && !recentFiles.includes(f)) recentFiles.push(f);
      if (recentFiles.length >= 12) break;
    }
  } catch {
    /* 還沒開始寫進度 */
  }
  let status: ScanStatus["status"] = "running";
  let error: string | null = null;
  if (report) status = "done";
  else if (exit && exit.code !== 0) {
    status = "failed";
    try {
      error = fs.readFileSync(path.join(d, "worker.log"), "utf8").trim().split("\n").slice(-6).join("\n");
    } catch {
      error = null;
    }
  }
  return { meta, status, progress, recentFiles, report, error };
}

export function listScans(): ScanSummary[] {
  if (!fs.existsSync(DATA_DIR)) return [];
  return fs
    .readdirSync(DATA_DIR)
    .map((id) => {
      const s = getScan(id);
      return s && { id, project: s.meta.project, path: s.meta.path, started_at: s.meta.started_at, status: s.status, score: s.report?.score ?? null, summary: s.report?.summary ?? null };
    })
    .filter((s): s is ScanSummary => Boolean(s))
    .sort((a, b) => b.started_at.localeCompare(a.started_at));
}
