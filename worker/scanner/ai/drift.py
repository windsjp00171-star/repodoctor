"""AI 檢查：規範落差（CLAUDE.md 寫的 vs 程式實際寫的）。

分兩步，讓 AI 只做判斷題（全域 Rule 5）：
1. AI 從規範檔「抽取」可以用搜尋驗證的規則（每條附一個 regex 與允許出現的檔案）
2. 程式用 regex 搜尋整個專案，收集違規證據——這一步是確定性的
3. 有證據時，AI 判斷證據是不是真的違規，並寫說明與修復指令

沒有證據就不打第二次，省錢。
"""
from __future__ import annotations

import fnmatch
import re

import config
from scanner.ai.client import AICheckError, AIClient
from scanner.ai.common import FINDINGS_SCHEMA, WRITING_RULES, coverage, to_findings
from scanner.files import Project
from scanner.masking import Masker
from scanner.rules.candidates import _is_test

SPEC_FILES = ["CLAUDE.md", "AGENTS.md", ".cursorrules", ".github/copilot-instructions.md", "docs/CLAUDE.md"]
MAX_SPEC_CHARS = 60_000
MAX_EVIDENCE_PER_RULE = 12
MAX_RULES = 20

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"},
                    "pattern": {"type": "string"},
                    "allowed_paths": {"type": "array", "items": {"type": "string"}},
                    "file_glob": {"type": "string"},
                },
                "required": ["rule", "pattern", "allowed_paths", "file_glob"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["rules"],
    "additionalProperties": False,
}

EXTRACT_SYSTEM = """你會收到一份專案規範（CLAUDE.md 之類）。請從裡面抽出「可以用搜尋程式碼來驗證」的規則。

只抽這一種：「某種寫法只能出現在某些檔案」或「某種寫法不可以出現」。例如：
- 「只在 db.py 建立 Supabase client」→ pattern `create_client\\(`、allowed_paths ["db.py"]、file_glob "*.py"
- 「禁止在 route 裡手寫 if not session.get('user_id')」→ pattern `if not session\\.get\\(['\\"]user_id`、allowed_paths []、file_glob "*.py"
- 「不要用 date.today()」→ pattern `date\\.today\\(\\)`、allowed_paths []、file_glob "*.py"

規則：
- pattern 是 Python 正規表示式，逐行比對，要夠精準、不要太寬（寧可漏抓，不要誤抓）
- allowed_paths：允許出現這個寫法的檔案路徑（可以用 * 萬用字元）；完全禁止就給 []
- file_glob：要搜尋哪些檔案，例如 "*.py"、"*.html"、"*"
- rule：用繁體中文寫一句規則原文的重點
- 做不到用搜尋驗證的規則（風格、流程、「要先問使用者」這類）一律不要抽
- 最多 20 條。規範裡沒有這類規則就回傳空陣列
"""

JUDGE_SYSTEM = """你在幫不會寫程式的人檢查「專案規範寫的」和「程式實際寫的」有沒有對不上。

你會收到幾條規範，每條附上搜尋找到、疑似違反的程式碼行。請判斷每一條：
- 真的違反 → 報告，一條規範最多報一個問題（把同一條的多處違規寫在同一個問題裡）
- 搜尋誤抓（例如出現在註解、字串、測試、或其實是規範允許的例外）→ 不要報
severity 一般用 medium；違反的是權限、金鑰、資料寫入這類規範時用 high。
file_path 填第一處違規的檔案，line 填那一行。

""" + WRITING_RULES


def _spec_text(proj: Project) -> tuple[str | None, str | None]:
    for name in SPEC_FILES:
        f = proj.get(name)
        if f and f.text:
            return name, f.text
    return None, None


def _matches_any(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path.rsplit("/", 1)[-1], g) or path.endswith("/" + g) or path == g
               for g in globs)


def run(proj: Project, ai: AIClient, masker: Masker) -> tuple[list, dict]:
    spec_name, spec = _spec_text(proj)
    if not spec:
        return [], {"status": "not_applicable", "note": "沒有 CLAUDE.md / AGENTS.md 之類的規範檔"}
    # 規範檔不能超過這一家單次能送的量（Groq 免費額度比較小），留 500 字給前後說明
    spec_limit = min(MAX_SPEC_CHARS, config.max_input_chars("drift") - 500)
    truncated = len(spec) > spec_limit
    spec_masked = masker.mask(spec[:spec_limit])

    try:
        extracted = ai.ask("drift", EXTRACT_SYSTEM, f"規範檔 `{spec_name}`：\n\n{spec_masked}", EXTRACT_SCHEMA)
    except AICheckError as e:
        return [], coverage(0, [str(e)], 0, 0, {}, "抽取規範失敗")

    rules, bad_patterns = [], 0
    for r in extracted.get("rules", [])[:MAX_RULES]:
        if len(r["pattern"]) > 200:
            bad_patterns += 1
            continue
        try:
            rules.append((r, re.compile(r["pattern"])))
        except re.error:
            bad_patterns += 1

    files = [f for f in proj.files if f.text and not _is_test(f.path)
             and not f.path.endswith((".md", ".lock", "package-lock.json"))]
    evidence_blocks, sent_files, n_hits = [], {spec_name}, 0
    for idx, (r, rx) in enumerate(rules, 1):
        hits = []
        for f in files:
            if not fnmatch.fnmatch(f.name, r["file_glob"] or "*"):
                continue
            if r["allowed_paths"] and _matches_any(f.path, r["allowed_paths"]):
                continue
            for i, ln in enumerate(f.lines, 1):
                if rx.search(ln[:500]):
                    hits.append((f.path, i, ln.strip()[:240]))
                    if len(hits) >= MAX_EVIDENCE_PER_RULE:
                        break
            if len(hits) >= MAX_EVIDENCE_PER_RULE:
                break
        if hits:
            n_hits += len(hits)
            sent_files |= {p for p, _, _ in hits}
            ev = "\n".join(f"- `{p}` 第 {i} 行：`{masker.mask(t)}`" for p, i, t in hits)
            evidence_blocks.append(f"## 規範 {idx}：{r['rule']}\n允許的檔案：{r['allowed_paths'] or '無（完全禁止）'}\n{ev}")

    note = f"從 `{spec_name}` 抽出 {len(rules)} 條可驗證的規則，搜尋到 {n_hits} 處疑似違反"
    if truncated:
        note += f"；規範檔超過 {spec_limit:,} 字，只讀了前面"
    if bad_patterns:
        note += f"；{bad_patterns} 條規則的搜尋式無效，略過"
    if not evidence_blocks:
        return [], coverage(1, [], len(rules), 0, {}, note)

    # 證據太多時只送放得下的那幾條規範，並在報告裡寫出來（不可以默默少檢查）
    limit, kept, size = config.max_input_chars("drift"), [], 0
    for blk in evidence_blocks:
        if size + len(blk) + 2 > limit:
            break
        kept.append(blk)
        size += len(blk) + 2
    if len(kept) < len(evidence_blocks):
        note += f"；疑似違反的規範有 {len(evidence_blocks)} 條，單次送出有上限，只判斷了前 {len(kept)} 條"
    if not kept:
        return [], coverage(1, ["單一規範的證據就超過單次送出上限"], len(rules), 0, {}, note)
    try:
        data = ai.ask("drift", JUDGE_SYSTEM, "\n\n".join(kept), FINDINGS_SCHEMA)
    except AICheckError as e:
        return [], coverage(1, [str(e)], len(rules), 0, {}, note)
    findings, dropped = to_findings(data, "drift", "ai.drift", sent_files)
    return findings, coverage(2, [], len(rules), 0, dropped, note)
