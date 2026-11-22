"""重複與散落：規則先找「確定的事實」直接報告，再挑出「需要判斷的候選」交給 AI。

確定的事實（不花錢）：
- Supabase client 在 db.py（或 lib/supabase/*）以外被建立
- 登入/權限 decorator 在不同檔案各自定義了好幾份

需要判斷的候選（給 AI）：
- 同名函式出現在好幾個檔案——是真的重複，還是只是剛好同名？
"""
from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass

from scanner.files import FileInfo, Project
from scanner.findings import Finding

_JS_CLIENT_RE = re.compile(r"\bcreate(?:Browser|Server)?Client\s*\(")
_ALLOWED_CLIENT_FILES = re.compile(r"(^|/)(db\.py|supabase_client\.py|lib/supabase/(client|server|admin)\.[jt]sx?)$")

_GUARD_NAMES = {"login_required", "admin_required", "super_admin_required", "staff_required",
                "pastor_required", "require_login", "require_admin", "require_staff", "require_pastor",
                "line_login_required", "auth_required", "requires_auth"}
_PY_DEF_RE = re.compile(r"(?m)^([ \t]*)def\s+([A-Za-z_]\w*)\s*\(")
_JS_DEF_RE = re.compile(r"(?m)^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\(|^\s*(?:export\s+)?const\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\(")

_COMMON_NAMES = {"main", "index", "get", "post", "put", "delete", "patch", "setup", "init", "run", "handler",
                 "create_app", "render", "home", "app", "helper", "wrapper", "decorator", "inner", "decorated",
                 "load", "save", "update", "list", "detail", "view", "page", "default", "test", "callback",
                 "upgrade", "downgrade", "ready", "start", "stop", "close", "open", "fetch", "middleware",
                 "Page", "Layout", "RootLayout", "GET", "POST", "PUT", "DELETE", "PATCH", "loader", "action"}


def _py_calls(text: str, name: str) -> list[int]:
    """用 AST 找真的函式呼叫（字串、註解裡提到的不算）。語法錯誤的檔案退回 0 筆。"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if (isinstance(fn, ast.Name) and fn.id == name) or (isinstance(fn, ast.Attribute) and fn.attr == name):
                out.append(node.lineno)
    return sorted(out)


def _is_test(path: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.py$|\.(test|spec)\.[jt]sx?$", path))


def _non_test_code(proj: Project) -> list[FileInfo]:
    return [f for f in proj.code_files() if not _is_test(f.path)]


@dataclass
class DupGroup:
    name: str
    sites: list[tuple[str, int, str]]   # (path, line, 函式本體前幾十行)


def _py_body(lines: list[str], start: int, indent: int, max_lines: int = 40) -> str:
    out = [lines[start]]
    for ln in lines[start + 1:start + 1 + 200]:
        if ln.strip() and (len(ln) - len(ln.lstrip())) <= indent and not ln.lstrip().startswith(("@", "#", ")")):
            break
        out.append(ln)
        if len(out) >= max_lines:
            break
    return "\n".join(out)


def _defs(f: FileInfo):
    lines = f.lines
    if f.ext == ".py":
        for m in _PY_DEF_RE.finditer(f.text):
            if m.group(1):                   # 只看最外層函式（巢狀的 wrapper 不算）
                continue
            ln = f.text.count("\n", 0, m.start())
            yield m.group(2), ln + 1, _py_body(lines, ln, 0)
    else:
        for m in _JS_DEF_RE.finditer(f.text):
            name = m.group(1) or m.group(2)
            ln = f.text.count("\n", 0, m.start())
            yield name, ln + 1, "\n".join(lines[ln:ln + 40])


def scan(proj: Project) -> tuple[list[Finding], list[DupGroup]]:
    out: list[Finding] = []
    code = _non_test_code(proj)

    # ── Supabase client 散落 ──
    sites = []
    for f in code:
        if _ALLOWED_CLIENT_FILES.search(f.path):
            continue
        if "supabase" not in f.text.lower():
            continue
        if f.ext == ".py":
            sites += [(f.path, ln) for ln in _py_calls(f.text, "create_client")]
        else:
            for m in _JS_CLIENT_RE.finditer(f.text):
                line = f.lines[f.text.count("\n", 0, m.start())].lstrip()
                if not line.startswith(("//", "*", "/*")):
                    sites.append((f.path, f.text.count("\n", 0, m.start()) + 1))
    has_db = any(re.search(r"(^|/)db\.py$", f.path) for f in proj.files)
    files = sorted({p for p, _ in sites})
    # 只有一個檔案在建立 client，那它就是「統一的地方」，不算散落
    if proj.uses_supabase() and (len(files) >= 2 or (has_db and files)):
        out.append(Finding(
            category="duplication", severity="medium",
            title=f"資料庫連線在 {len(files)} 個地方各自建立",
            plain_explanation=(f"Supabase 連線應該只在一個地方建立，其他地方共用。現在 {len(files)} 個檔案各自建了一份："
                               + "、".join(f"`{p}`" for p in files[:5])
                               + "。之後要換金鑰、加設定，很容易改了一個忘了另一個。"),
            advanced_explanation="在 " + "、".join(f"`{p}:{l}`" for p, l in sites[:8]) + " 呼叫 create_client。"
                                 + ("專案已有 `db.py`。" if has_db else ""),
            fix_prompt=("請把 Supabase client 統一到一個地方建立：\n"
                        f"1. 要改：{'沿用既有的 `db.py`' if has_db else '新增 `db.py`'}，只在那裡 `create_client`；"
                        + "、".join(f"`{p}`" for p in files) + " 改成 `from db import supabase`。\n"
                        "2. 如果某個檔案刻意用不同的金鑰（例如 service role vs anon），先列給我看，不要直接合併。\n"
                        "3. 不可以動到：查詢邏輯本身。\n"
                        "4. 驗證：整個專案搜尋 `create_client(` 只剩 db.py 一處；程式能正常啟動。"),
            rule_id="duplication.db_client", file_path=files[0],
            fingerprint_key="db_client", extra={"sites": [{"file": p, "line": l} for p, l in sites]},
        ))

    # ── 登入/權限 decorator 定義好幾份 ──
    by_name: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for f in code:
        for name, line, body in _defs(f):
            by_name[name].append((f.path, line, body))
    for name in sorted(_GUARD_NAMES & set(by_name)):
        files = sorted({p for p, _, _ in by_name[name]})
        if len(files) < 2:
            continue
        out.append(Finding(
            category="duplication", severity="medium",
            title=f"{name} 被寫了 {len(files)} 份",
            plain_explanation=(f"登入／權限檢查 `{name}` 在 {len(files)} 個檔案各寫了一份。"
                               f"改了其中一份（例如加上封鎖帳號的檢查），另外幾份不會跟著改，就會有頁面漏掉。"),
            advanced_explanation="定義位置：" + "、".join(f"`{p}:{l}`" for p, l, _ in by_name[name]),
            fix_prompt=(f"`{name}` 在這些檔案各定義了一份：" + "、".join(f"`{p}`" for p in files) + "。請幫我：\n"
                        f"1. 先比較這幾份的差異，列給我看，**等我決定要以哪一份為準**。\n"
                        f"2. 決定後只保留一份（放在 decorators 檔），其他檔案改成 import 它。\n"
                        f"3. 不可以動到：哪些路由有套用這個 decorator——一個都不能少。\n"
                        f"4. 驗證：整個專案 `def {name}` 只剩一處；原本需要登入的頁面，沒登入時仍然被擋下。"),
            rule_id="duplication.guard", fingerprint_key=name,
        ))

    # ── 給 AI 判斷的候選：同名函式散在好幾個檔案 ──
    groups = []
    for name, defs in by_name.items():
        files = {p for p, _, _ in defs}
        if len(files) < 2 or name in _GUARD_NAMES or name in _COMMON_NAMES or name.startswith("_") and len(name) < 4:
            continue
        if all(len(b.splitlines()) < 4 for _, _, b in defs):
            continue
        groups.append(DupGroup(name, defs[:4]))
    groups.sort(key=lambda g: -len({p for p, _, _ in g.sites}))
    return out, groups
