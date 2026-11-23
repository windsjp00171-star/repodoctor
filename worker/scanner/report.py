"""組出 JSON 報告：分數、問題排序、每一項檢查的完成狀態、token 用量。"""
from __future__ import annotations

from collections import Counter

import config
from scanner.findings import CATEGORIES, SEVERITY_ORDER, Finding

PENALTY = {"critical": 40, "high": 20, "medium": 8, "low": 3}
SCORE_NOTE = "分數公式是初稿：每類 100 分，緊急扣 40、高扣 20、中扣 8、低扣 3；有緊急問題總分最高 59。沒檢查完的類別不計分。"


def scores(findings: list[Finding], coverage: dict[str, dict]) -> tuple[int | None, dict]:
    cat_scores: dict[str, int | None] = {}
    for cat in CATEGORIES:
        if coverage.get(cat, {}).get("status") in ("failed", "skipped", None):
            cat_scores[cat] = None
            continue
        cat_scores[cat] = max(0, 100 - sum(PENALTY[f.severity] for f in findings if f.category == cat))
    vals = [v for v in cat_scores.values() if v is not None]
    if not vals:
        return None, cat_scores
    total = round(sum(vals) / len(vals))
    if any(f.severity == "critical" for f in findings):
        total = min(total, 59)
    return total, cat_scores


def _languages(proj) -> list[str]:
    names = {f.path.lower() for f in proj.files}
    langs = []
    if any(n.endswith(".py") for n in names):
        langs.append("python")
        if "manage.py" in names:
            langs.append("django")
        elif proj.uses("from flask"):
            langs.append("flask")
    if any(n.endswith((".ts", ".tsx")) for n in names):
        langs.append("typescript")
    elif any(n.endswith((".js", ".jsx")) for n in names):
        langs.append("javascript")
    if any(n.startswith("next.config") for n in names):
        langs.append("nextjs")
    if proj.uses_supabase():
        langs.append("supabase")
    return langs


def build(proj, findings: list[Finding], coverage: dict, usage: dict, started: str, finished: str,
          payloads: list | None = None) -> dict:
    findings = sorted(findings, key=lambda f: (SEVERITY_ORDER.index(f.severity), f.category, f.file_path or "", f.line or 0))
    total, cat_scores = scores(findings, coverage)
    counts = Counter(f.severity for f in findings)
    report = {
        "tool": "repodoctor-worker",
        "version": config.VERSION,
        "project": proj.root.name,
        "commit_sha": proj.commit_sha,
        "has_git": proj.has_git,
        "languages": _languages(proj),
        "files_scanned": len(proj.files),
        "started_at": started,
        "finished_at": finished,
        "score": total,
        "category_scores": cat_scores,
        "score_note": SCORE_NOTE,
        "summary": {s: counts.get(s, 0) for s in SEVERITY_ORDER},
        "coverage": coverage,
        "findings": [f.to_dict() for f in findings],
        "token_usage": usage,
        "map": None,   # 白話地圖：Phase 2
    }
    if payloads is not None:
        report["dry_run_payloads"] = payloads
    return report
