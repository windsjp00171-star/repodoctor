"""AI 檢查：重複與散落。

確定的重複（Supabase client、登入 decorator）規則已經報了；這裡只處理「同名函式散在
好幾個檔案」這種要看內容才知道是不是真的重複的候選。
"""
from __future__ import annotations

import config
from scanner.ai.client import AICheckError, AIClient
from scanner.ai.common import FINDINGS_SCHEMA, WRITING_RULES, coverage, pack, to_findings
from scanner.masking import Masker
from scanner.rules.candidates import DupGroup

SYSTEM = """你在幫不會寫程式的人檢查專案裡「同一件事被寫了好幾份」的問題。

你會收到幾組「同名函式出現在不同檔案」的片段。每一組請判斷：
- 是真的重複：做的是同一件事、邏輯幾乎一樣 → 報告，建議收成一份共用
- 只是剛好同名、做的事不一樣（例如不同頁面各自的 index） → 不要報
- 一份是另一份的舊版／複製後改壞的 → 報告，並指出差異

一組最多報一個問題，file_path 填其中一個檔案、line 填那個函式的行號。
重複本身不會讓系統壞掉，severity 一般是 medium；只有在重複的是權限、金額、資料寫入這類「改了一份忘了另一份就會出事」的邏輯時才用 high。

""" + WRITING_RULES


def run(groups: list[DupGroup], ai: AIClient, masker: Masker) -> tuple[list, dict]:
    if not groups:
        return [], {"status": "not_applicable", "note": "沒有同名函式散在多個檔案"}
    units = []
    for g in groups:
        parts = [f"## 第 {len(units) + 1} 組：`{g.name}`（出現在 {len({p for p, _, _ in g.sites})} 個檔案）"]
        for path, line, body in g.sites:
            lines = body.splitlines()
            numbered_body = "\n".join(f"{line + i:>5} | {ln[:300]}" for i, ln in enumerate(lines))
            parts.append(f"### {path}（第 {line}–{line + len(lines) - 1} 行）\n```\n{masker.mask(numbered_body)}\n```")
        # 一組裡有好幾個檔案，用 \0 串起來讓 pack 記住全部
        units.append(("\0".join(sorted({p for p, _, _ in g.sites})), "\n\n".join(parts)))

    requests, skipped = pack([], units, config.MAX_INPUT_CHARS_PER_CALL, config.MAX_CALLS_PER_CHECK)
    findings, dropped, errors, ok = [], {}, [], 0
    for body, sent in requests:
        sent_files = {p for s in sent for p in s.split("\0")}
        try:
            data = ai.ask("duplication", SYSTEM, "請判斷以下每一組是不是真的重複：\n\n" + body, FINDINGS_SCHEMA)
        except AICheckError as e:
            errors.append(str(e))
            break
        ok += 1
        fs, d = to_findings(data, "duplication", "ai.duplication", sent_files)
        findings += fs
        for k, v in d.items():
            dropped[k] = dropped.get(k, 0) + v
    return findings, coverage(ok, errors, len(units), skipped, dropped,
                              f"送出 {len(units) - skipped}/{len(units)} 組同名函式")
