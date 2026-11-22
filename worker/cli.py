"""RepoDoctor 健檢引擎（Phase 0）命令列工具。

    python -m cli <資料夾> [-o report.json] [--no-ai] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from scanner.ai import auth as ai_auth
from scanner.ai import drift as ai_drift
from scanner.ai import duplication as ai_dup
from scanner.ai.client import AIClient
from scanner.files import load_project
from scanner.findings import SEVERITIES
from scanner.masking import Masker
from scanner.report import build
from scanner.rules import candidates, hygiene, secrets, supabase_rls


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Progress:
    """把進度寫成 JSON Lines（對應 SPEC scans 表的 progress、current_file）。網站讀最後一行。"""

    def __init__(self, path: str | None):
        self.fp = open(path, "a", encoding="utf-8") if path else None
        self.found = 0

    def emit(self, progress: int, stage: str, current_file: str | None = None, found: int | None = None):
        if found is not None:
            self.found = found
        if self.fp:
            self.fp.write(json.dumps({"progress": progress, "stage": stage, "current_file": current_file,
                                      "found": self.found}, ensure_ascii=False) + "\n")
            self.fp.flush()


def scan(path: str, use_ai: bool = True, dry_run: bool = False, progress_file: str | None = None) -> dict:
    started = _now()
    prog = Progress(progress_file)
    prog.emit(1, "讀取專案")
    proj = load_project(path)
    coverage: dict[str, dict] = {}

    n = max(1, len(proj.files))
    step = max(1, n // 200)
    done = [0]

    def on_file(p, found):
        done[0] += 1
        if done[0] % step == 0:
            prog.emit(5 + 35 * done[0] // n, "檢查金鑰外洩", p, found)

    findings = secrets.scan(proj, on_file=on_file)
    prog.emit(40, "檢查資料庫權限", found=len(findings))
    coverage["secrets"] = {"status": "done", "note": f"掃描 {len(proj.files)} 個檔案"
                           + ("；有 git：只看會被 commit 的檔案，並檢查歷史裡的 .env 類檔名" if proj.has_git else "；沒有 git，無法判斷檔案有沒有 commit")}
    db = supabase_rls.scan(proj)
    findings += db
    coverage["database"] = ({"status": "done", "note": "只看 SQL migration 檔，看不到線上資料庫"} if proj.uses_supabase()
                            else {"status": "not_applicable", "note": "沒有用 Supabase"})
    prog.emit(48, "檢查專案衛生", found=len(findings))
    findings += hygiene.scan(proj)
    coverage["hygiene"] = {"status": "done", "note": ""}
    prog.emit(55, "找重複與散落", found=len(findings))
    dup_rule, dup_groups = candidates.scan(proj)
    findings += dup_rule

    masker = Masker()
    for f in proj.files:
        masker.learn(f)
    ai = AIClient(masker, dry_run=dry_run)

    if use_ai or dry_run:
        prog.emit(60, "AI 檢查登入與權限", found=len(findings))
        fs, coverage["auth"] = ai_auth.run(proj, ai, masker)
        findings += fs
        prog.emit(80, "AI 判斷重複", found=len(findings))
        fs, cov = ai_dup.run(dup_groups, ai, masker)
        findings += fs
        coverage["duplication"] = {"status": "done" if cov["status"] == "not_applicable" else cov["status"],
                                   "note": f"規則找到 {len(dup_rule)} 個確定的重複；AI：{cov['note']}"}
        prog.emit(90, "AI 比對規範", found=len(findings))
        fs, coverage["drift"] = ai_drift.run(proj, ai, masker)
        findings += fs
    else:
        coverage["auth"] = {"status": "skipped", "note": "--no-ai"}
        coverage["duplication"] = {"status": "partial", "note": f"只跑了規則（找到 {len(dup_rule)} 個）；同名函式的 AI 判斷因 --no-ai 略過"}
        coverage["drift"] = {"status": "skipped", "note": "--no-ai"}

    report = build(proj, findings, coverage, ai.usage.to_dict(), started, _now(),
                   payloads=ai.payloads if dry_run else None)
    prog.emit(100, "完成", found=len(findings))
    return report


def _summary(r: dict) -> str:
    lines = [f"RepoDoctor 健檢：{r['project']}　總分 {r['score'] if r['score'] is not None else '—'}"]
    lines.append("　".join(f"{SEVERITIES[k]} {v}" for k, v in r["summary"].items()))
    for cat, cov in r["coverage"].items():
        lines.append(f"  [{cov['status']}] {cat}：{cov['note']}")
    t = r["token_usage"]["total"]
    tag = "（dry-run 估計）" if r["token_usage"]["estimated"] else ""
    lines.append(f"token：輸入 {t['input_tokens']:,}／輸出 {t['output_tokens']:,}，"
                 f"約 US${t['cost_usd']:.4f}（NT${t['cost_twd']:.2f}）{tag}")
    for f in r["findings"][:15]:
        loc = f"{f['file_path']}:{f['line']}" if f["line"] else (f["file_path"] or "")
        lines.append(f"  - [{f['severity_label']}] {f['title']}　{loc}")
    if len(r["findings"]) > 15:
        lines.append(f"  …還有 {len(r['findings']) - 15} 個，見 JSON")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="repodoctor", description="RepoDoctor 健檢引擎：輸入本機資料夾，輸出 JSON 健檢報告")
    ap.add_argument("path", help="要健檢的專案資料夾")
    ap.add_argument("-o", "--output", help="報告寫到這個檔案（預設印到標準輸出）")
    ap.add_argument("--no-ai", action="store_true", help="只跑規則掃描，不呼叫 Claude API")
    ap.add_argument("--dry-run", action="store_true", help="列出會送給 AI 的內容（已遮罩）與預估 token，不呼叫 API")
    ap.add_argument("--progress-file", help="把進度一行一筆寫到這個檔案（給網站用）")
    ap.add_argument("-q", "--quiet", action="store_true", help="不印摘要")
    args = ap.parse_args(argv)

    report = scan(args.path, use_ai=not args.no_ai, dry_run=args.dry_run, progress_file=args.progress_file)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fp:
            fp.write(text)
        if not args.quiet:
            print(_summary(report), file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
