"""AI 檢查共用的回傳格式，以及把 AI 回答轉成 Finding 的地方。"""
from __future__ import annotations

from scanner.findings import Finding

FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "subject": {"type": "string"},
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "file_path": {"type": "string"},
                    "line": {"type": "integer"},
                    "plain_explanation": {"type": "string"},
                    "advanced_explanation": {"type": "string"},
                    "fix_prompt": {"type": "string"},
                },
                "required": ["title", "subject", "severity", "confidence", "file_path", "line",
                             "plain_explanation", "advanced_explanation", "fix_prompt"],
                "additionalProperties": False,
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["findings", "notes"],
    "additionalProperties": False,
}

WRITING_RULES = """\
寫作規則（每一個問題都要遵守）：
- 全部用繁體中文。讀者是用 AI 寫程式的新手，看不懂技術名詞。
- title：一句話講問題，20 字以內，例如「這 3 個頁面沒登入也能進」。
- plain_explanation：白話講「哪裡有問題、為什麼危險」，2–3 句，不要出現程式碼。
- advanced_explanation：給懂程式的人，可以有檔名、函式名、行號。
- fix_prompt：一段可以直接貼給 Claude Code 的中文指令，一定要包含四件事：
  1. 要改哪些檔案、改成什麼樣子
  2. 不可以動到什麼
  3. 改完怎麼驗證
  （需要使用者先做決定的地方，要寫「先列給我看，等我確認再動手」）
- subject：這個問題針對的對象（函式名、路由網址、或規範條目），用來比較前後兩次健檢，要穩定、不要加修飾。
- file_path 和 line 只能填我給你的片段裡真的出現的檔案與行號。
- confidence：你有多確定這是真的問題。只看到片段、不確定全貌時填 low。
- 寧可少報，不要誤報。看不出問題就回傳空的 findings，不要湊數。
- 程式碼裡的 [已遮罩#N] 是被遮掉的金鑰，不是問題本身，不要針對它報告。
"""


def to_findings(data: dict, category: str, rule_id: str, sent_files: set[str]) -> tuple[list[Finding], dict]:
    """把 AI 回答轉成 Finding。會丟掉：低信心的、引用了沒送過的檔案的（模型自己編的）。"""
    out, dropped = [], {"low_confidence": 0, "unknown_file": 0}
    for item in data.get("findings", []):
        if item.get("confidence") == "low":
            dropped["low_confidence"] += 1
            continue
        path = item.get("file_path", "").removeprefix("./")
        if path not in sent_files:
            dropped["unknown_file"] += 1
            continue
        out.append(Finding(
            category=category, severity=item["severity"], title=item["title"],
            plain_explanation=item["plain_explanation"], advanced_explanation=item["advanced_explanation"],
            fix_prompt=item["fix_prompt"], rule_id=rule_id, file_path=path, line=item.get("line") or None,
            source="ai", confidence=item["confidence"], fingerprint_key=item.get("subject") or item["title"],
        ))
    return out, dropped


# ── 片段打包 ──

def numbered(path: str, lines: list[str], start: int, end: int, max_line_len: int = 300) -> str:
    """把第 start..end 行（1 起算，含頭尾）包成帶行號的片段，讓模型能引用行號。"""
    body = "\n".join(f"{i:>5} | {ln[:max_line_len]}" for i, ln in enumerate(lines[start - 1:end], start))
    return f"### {path}（第 {start}–{end} 行）\n```\n{body}\n```"


def pack(context: list[str], units: list[tuple[str, str]], max_chars: int, max_calls: int) -> tuple[list[tuple[str, set[str]]], int]:
    """把片段塞進最多 max_calls 次請求。context 每次都帶；units 是 (檔案路徑, 片段)。

    回傳 [(這次的 units 文字, 這次送了哪些檔案（含 context 的）)]，以及塞不下而沒送的片段數。
    context 文字由呼叫端自己放進 prompt（這裡只替它保留空間）。
    """
    ctx = "\n\n".join(context)
    budget = max_chars - len(ctx) - 2000
    calls: list[tuple[list[str], set[str]]] = []
    cur, cur_files, size, skipped = [], set(), 0, 0
    for path, text in units:
        if len(text) > budget:
            skipped += 1
            continue
        if size + len(text) > budget:
            calls.append((cur, cur_files))
            cur, cur_files, size = [], set(), 0
            if len(calls) >= max_calls:
                skipped += 1
                continue
        if len(calls) >= max_calls:
            skipped += 1
            continue
        cur.append(text)
        cur_files.add(path)
        size += len(text) + 2
    if cur and len(calls) < max_calls:
        calls.append((cur, cur_files))
    ctx_files = {line.split("（")[0][4:] for line in context if line.startswith("### ")}
    return [("\n\n".join(c), files | ctx_files) for c, files in calls], skipped


def coverage(ok_calls: int, errors: list[str], total_units: int, skipped: int, dropped: dict, note: str) -> dict:
    """一個 AI 檢查的完成狀態。失敗不可以被讀成「沒有問題」。"""
    if errors and ok_calls == 0:
        status = "failed"
    elif errors or skipped:
        status = "partial"
    else:
        status = "done"
    if skipped:
        note += f"；{skipped} 個片段超過上限沒有檢查"
    if errors:
        note += "；中斷原因：" + "；".join(errors)
    if any(dropped.values()):
        note += f"；略過 {dropped.get('low_confidence', 0)} 個低信心、{dropped.get('unknown_file', 0)} 個引用了沒送過的檔案的回答"
    return {"status": status, "note": note}
