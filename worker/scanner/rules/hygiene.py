"""規則掃描：專案衛生。"""
from __future__ import annotations

import re
import subprocess

import config
from scanner.files import Project
from scanner.findings import Finding

_DEAD_NAME_RE = re.compile(r"(?i)(\.bak|\.orig|\.old|~)$|[ _\-.](copy|old|backup|bak)\.\w+$| \(\d\)\.\w+$")


def _env_ignored(proj: Project) -> bool:
    if proj.has_git:
        r = subprocess.run(["git", "-C", str(proj.root), "check-ignore", "-q", "--no-index", ".env"],
                           capture_output=True)
        return r.returncode == 0
    gi = proj.get(".gitignore")
    return bool(gi and gi.text and re.search(r"(?m)^\s*/?\.env\*?\s*$|^\s*\*\.env\s*$|^\s*\.env\.?\*?", gi.text))


def _uses_env(proj: Project) -> bool:
    return any(f.text and re.search(r"os\.environ|os\.getenv|process\.env|load_dotenv|import\.meta\.env", f.text)
               for f in proj.code_files())


def scan(proj: Project) -> list[Finding]:
    out: list[Finding] = []
    root_names = {f.path.lower() for f in proj.files if "/" not in f.path}

    if not any(n.startswith("readme") for n in root_names):
        out.append(Finding(
            category="hygiene", severity="low", title="沒有 README",
            plain_explanation="專案最外層沒有 README。過一陣子你自己、或接手的人，會不知道這個專案在做什麼、怎麼啟動。",
            advanced_explanation="根目錄沒有 README.md / README。",
            fix_prompt=("請幫我在專案最外層建立 `README.md`，用繁體中文寫：\n"
                        "1. 內容：這個專案在做什麼（一兩句）、怎麼安裝、怎麼啟動、需要哪些環境變數（只列名字，不要寫值）。\n"
                        "2. 先讀過程式再寫，不要猜；不確定的地方標「待確認」。\n"
                        "3. 不可以動到：任何程式碼。\n"
                        "4. 驗證：照著 README 的步驟，能在一台新電腦把專案跑起來。"),
            rule_id="hygiene.no_readme",
        ))

    if ".gitignore" not in root_names:
        out.append(Finding(
            category="hygiene", severity="medium" if _uses_env(proj) else "low", title="沒有 .gitignore",
            plain_explanation="沒有 .gitignore，git 會把資料夾裡所有東西都收進去，包括放金鑰的 .env、暫存檔、上百 MB 的套件資料夾。",
            advanced_explanation="根目錄沒有 .gitignore。",
            fix_prompt=("請幫我在專案最外層建立 `.gitignore`：\n"
                        "1. 內容：依這個專案用的語言，擋掉 `.env`、`.env.*`（保留 `.env.example`）、虛擬環境、`node_modules`、`__pycache__`、建置產物。\n"
                        "2. 不可以動到：程式碼。\n"
                        "3. 驗證：`git status` 不再出現這些檔案；`git check-ignore .env` 有輸出。"),
            rule_id="hygiene.no_gitignore",
        ))
    elif _uses_env(proj) and not _env_ignored(proj):
        out.append(Finding(
            category="hygiene", severity="medium", title=".gitignore 沒有擋 .env",
            plain_explanation="程式會讀環境變數，但 .gitignore 沒有擋 `.env`。哪天你建了 .env 放金鑰，一個 `git add .` 就推上 GitHub 了。",
            advanced_explanation="`git check-ignore .env` 沒有命中。",
            fix_prompt=("請在 `.gitignore` 加上：\n```\n.env\n.env.*\n!.env.example\n```\n"
                        "不可以動到：.gitignore 其他既有的規則。\n驗證：`git check-ignore .env` 有輸出。"),
            rule_id="hygiene.env_not_ignored", file_path=".gitignore",
        ))

    for f in proj.files:
        if f.size > config.HUGE_FILE_BYTES:
            out.append(Finding(
                category="hygiene", severity="low", title=f"{f.name} 有 {f.size // 1_000_000} MB",
                plain_explanation=f"`{f.path}` 是一個很大的檔案。放在 git 裡會讓每次 clone 都變慢，GitHub 也有單檔 100 MB 的上限。",
                advanced_explanation=f"`{f.path}`：{f.size:,} bytes。",
                fix_prompt=(f"`{f.path}` 很大（{f.size // 1_000_000} MB）。請先告訴我這個檔案是做什麼用的、程式有沒有讀它，"
                            f"再建議要搬到哪裡（例如雲端儲存、Git LFS，或改成執行時下載）。先不要刪除或搬動。"),
                rule_id="hygiene.huge_file", file_path=f.path,
            ))
        elif f.ext in config.CODE_EXTS and f.text and ".min." not in f.name:
            n = len(f.lines)
            if n > config.LONG_FILE_LINES:
                out.append(Finding(
                    category="hygiene", severity="low", title=f"{f.name} 有 {n:,} 行",
                    plain_explanation=f"`{f.path}` 有 {n:,} 行。檔案太長，AI 每次修改都要讀很多不相干的東西，越改越容易出錯。",
                    advanced_explanation=f"`{f.path}`：{n:,} 行（門檻 {config.LONG_FILE_LINES}）。",
                    fix_prompt=(f"`{f.path}` 有 {n:,} 行，請幫我評估怎麼拆：\n"
                                f"1. 先列出這個檔案裡有哪幾群功能、各自大約幾行，提出拆成哪幾個檔案的方案，**等我確認再動手**。\n"
                                f"2. 拆的時候只搬移、不改邏輯；所有 import 跟著改好。\n"
                                f"3. 不可以動到：函式的行為、對外的網址或 API。\n"
                                f"4. 驗證：拆完後既有測試全部通過，程式能正常啟動。"),
                    rule_id="hygiene.long_file", file_path=f.path,
                ))
        if _DEAD_NAME_RE.search(f.name):
            out.append(Finding(
                category="hygiene", severity="low", title=f"疑似備份檔 {f.name}",
                plain_explanation=f"`{f.path}` 看檔名像是舊版或備份。留著的話，你或 AI 以後可能改錯檔案。",
                advanced_explanation=f"`{f.path}` 的檔名符合備份檔樣式。",
                fix_prompt=(f"`{f.path}` 看起來是備份檔。請先搜尋整個專案有沒有任何地方 import 或讀取它，"
                            f"把結果告訴我；沒有人用的話，再問我要不要刪掉。不要直接刪除。"),
                rule_id="hygiene.dead_file", file_path=f.path,
            ))
    return out
