"""規則掃描：金鑰外洩。說明與修復指令用固定模板，不花 AI 的錢。"""
from __future__ import annotations

from scanner.files import Project, is_env_like
from scanner.findings import Finding
from scanner.masking import allow_unquoted, for_report, preview
from scanner.secret_patterns import detect


def _fix_prompt(file: str, line: int, kind: str, p4: str, env: str, provider: str, committed: bool) -> str:
    rotate = (f"\n\n另外：這把金鑰已經在 git 紀錄裡，就算刪掉，舊的 commit 裡還看得到。"
              f"修好程式後請到「{provider}」把它作廢、換一把新的——這一步只有你能做，AI 做不到。") if committed else ""
    return (
        f"請幫我處理 `{file}` 第 {line} 行寫死的 `{kind}`（開頭是 `{p4}`）。\n"
        f"1. 要改的地方：把這個值從 `{file}` 拿掉，改成從環境變數 `{env}` 讀取；"
        f"在 `.env.example` 加一行 `{env}=`（值留空）當範例。\n"
        f"2. 確認 `.gitignore` 有擋 `.env`，沒有就加上。\n"
        f"3. 不可以動到：其他功能的程式邏輯；不要把真正的值寫進任何會被 commit 的檔案（包含註解、測試、README）。\n"
        f"4. 改完怎麼驗證：執行 `git grep -n \"{p4.rstrip('…')}\"` 確認整個專案找不到這串；"
        f"設定好環境變數後，程式能正常啟動。"
        + rotate
    )


def scan(proj: Project) -> list[Finding]:
    out: list[Finding] = []

    for f in proj.files:
        if not f.text:
            continue
        unq = allow_unquoted(f)
        lines = f.lines
        for s in detect(f.text, allow_unquoted=unq):
            if not s.confident:
                continue
            line_no = f.text.count("\n", 0, s.start) + 1
            committed = f.tracked is not False   # 沒有 git 時無法判斷，當成已 commit
            severity = s.severity if committed else "high"
            where = "已經 commit 進 git" if f.tracked else ("還沒 commit，但下一次 `git add` 就會進去" if f.tracked is False else "（沒有 git，無法判斷有沒有 commit）")
            out.append(Finding(
                category="secrets", severity=severity,
                title=f"{s.kind} 寫死在 {f.name}",
                plain_explanation=(f"{s.kind} 直接寫在 `{f.path}` 裡，{where}。"
                                   f"任何看得到這個專案的人，都能拿去用你的帳號、花你的錢。"),
                advanced_explanation=(f"`{f.path}:{line_no}` 偵測到 {s.kind}（開頭 `{preview(s.value)}`）。"
                                      f"金鑰應該放在環境變數，由部署平台注入，不進版本控制。"),
                fix_prompt=_fix_prompt(f.path, line_no, s.kind, preview(s.value), s.env_name or "SECRET_KEY",
                                       s.provider, committed and f.tracked is not None),
                rule_id="secrets.in_file", file_path=f.path, line=line_no,
                masked_snippet=for_report(lines[line_no - 1] if line_no <= len(lines) else "", unq),
                fingerprint_key=f"{s.kind}|{preview(s.value)}",
                extra={"key_prefix": preview(s.value), "committed": f.tracked},
            ))

        if is_env_like(f.name) and f.tracked:
            if not any(x.file_path == f.path for x in out):
                out.append(Finding(
                    category="secrets", severity="high",
                    title=f"{f.name} 被 commit 進 git",
                    plain_explanation=(f"`{f.path}` 是放金鑰用的檔案，卻被放進 git 了。"
                                       f"現在裡面看起來沒有真的金鑰，但只要有人填進去再 commit，就會外洩。"),
                    advanced_explanation=f"`{f.path}` 已被追蹤（git ls-files）。這類檔案應列入 .gitignore。",
                    fix_prompt=(f"請把 `{f.path}` 從 git 追蹤中移除，但保留我電腦上的檔案：\n"
                                f"1. 執行 `git rm --cached {f.path}`，並把它加進 `.gitignore`。\n"
                                f"2. 如果專案需要範例，另外建立 `.env.example`，只放變數名、不放值。\n"
                                f"3. 不可以動到：檔案內容本身、其他程式。\n"
                                f"4. 驗證：`git ls-files {f.path}` 沒有輸出；`git status` 不再顯示它。"),
                    rule_id="secrets.env_tracked", file_path=f.path,
                ))

    for path in proj.history_env_files:
        out.append(Finding(
            category="secrets", severity="critical",
            title=f"{path.rsplit('/', 1)[-1]} 曾經被 commit 過",
            plain_explanation=(f"`{path}` 現在已經不在專案裡了，但它曾經被 commit 過。"
                               f"git 會留下每一次的紀錄，任何人都還能從舊的 commit 把它挖出來。"),
            advanced_explanation=(f"`git log --all --diff-filter=A` 找到 `{path}`。這一版只檢查檔名，"
                                  f"沒有掃描舊 commit 的內容。"),
            fix_prompt=(f"`{path}` 曾經被 commit 過，裡面的金鑰要當成已經外洩。請幫我：\n"
                        f"1. 用 `git log --all -p -- {path}` 列出這個檔案曾經放過哪些變數名（只列名字，不要印出值）。\n"
                        f"2. 告訴我每個變數是哪個服務的金鑰、該去哪個後台作廢。\n"
                        f"3. 不可以動到：不要改寫 git 歷史、不要 force push——那要我自己決定。\n"
                        f"4. 驗證：確認 `.gitignore` 有擋這個檔名。\n"
                        f"作廢、換新金鑰這一步只有我能做。"),
            rule_id="secrets.in_history", file_path=path,
        ))
    return out
