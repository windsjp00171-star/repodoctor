"""規則掃描：Supabase 資料庫權限。

只看得到 migration 檔，看不到線上資料庫。報告裡要把這個限制講出來——
有人是在 Supabase 後台直接開 RLS 的，那就不是問題。
"""
from __future__ import annotations

import re

from scanner.files import Project
from scanner.findings import Finding

_COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)
_IDENT = r'(?:"?[A-Za-z_][\w]*"?\.)?"?([A-Za-z_][\w]*)"?'
_CREATE_RE = re.compile(r"(?i)\bcreate\s+(?:unlogged\s+)?table\s+(?:if\s+not\s+exists\s+)?" + _IDENT)
_CREATE_SCHEMA_RE = re.compile(r'(?i)\bcreate\s+(?:unlogged\s+)?table\s+(?:if\s+not\s+exists\s+)?"?([A-Za-z_]\w*)"?\.')
_ENABLE_RE = re.compile(r"(?i)\balter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?" + _IDENT + r"\s+enable\s+row\s+level\s+security")
_DISABLE_RE = re.compile(r"(?i)\balter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?" + _IDENT + r"\s+disable\s+row\s+level\s+security")
_DROP_RE = re.compile(r"(?i)\bdrop\s+table\s+(?:if\s+exists\s+)?" + _IDENT)
# 用迴圈一次幫所有表開 RLS（EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', ...)）
_DYNAMIC_ENABLE_RE = re.compile(r"(?is)execute\s+format\s*\(\s*'[^']*enable\s+row\s+level\s+security")

_FRONTEND_DIRS = ("static/", "public/", "templates/", "components/", "src/components/", "src/app/", "app/", "pages/")
_FRONTEND_EXTS = {".js", ".jsx", ".ts", ".tsx", ".html", ".vue", ".svelte", ".mjs"}
_SERVICE_REF_RE = re.compile(r"(?i)service[_-]?role|SUPABASE_SERVICE|SUPABASE_SECRET")
_NEXT_PUBLIC_SECRET_RE = re.compile(r"\bNEXT_PUBLIC_[A-Z0-9_]*(?:SERVICE_ROLE|SECRET)[A-Z0-9_]*\b")


def _is_frontend(path: str, text: str) -> bool:
    ext = path[path.rfind("."):].lower() if "." in path else ""
    if ext not in _FRONTEND_EXTS:
        return False
    if "/api/" in path or path.endswith(("route.ts", "route.js", "middleware.ts", "middleware.js")):
        return False
    if path.startswith(("app/", "src/app/", "pages/")) and ext in {".ts", ".tsx", ".js", ".jsx"}:
        return "use client" in text[:300]   # Next.js 只有 client component 會送到瀏覽器
    return path.startswith(_FRONTEND_DIRS) or "/static/" in path or "/templates/" in path or "use client" in text[:300]


def scan(proj: Project) -> list[Finding]:
    if not proj.uses_supabase():
        return []
    out: list[Finding] = []

    # ── service role key 出現在前端 ──
    for f in proj.files:
        if not f.text:
            continue
        js_or_env = f.ext in _FRONTEND_EXTS | {".cjs"} or f.name.lower().startswith(".env")
        for i, line in enumerate(f.lines if js_or_env else [], 1):
            m = _NEXT_PUBLIC_SECRET_RE.search(line)
            if m:
                out.append(Finding(
                    category="database", severity="critical",
                    title=f"{m.group(0)} 會被送到瀏覽器",
                    plain_explanation=(f"`{m.group(0)}` 開頭是 NEXT_PUBLIC_，Next.js 會把它打包進網頁。"
                                       f"任何人打開網站、按 F12 就看得到這把最高權限的鑰匙。"),
                    advanced_explanation=f"`{f.path}:{i}`：NEXT_PUBLIC_ 變數會內嵌到 client bundle。service role / secret key 只能在伺服器端使用。",
                    fix_prompt=(f"請把 `{m.group(0)}` 改成不帶 `NEXT_PUBLIC_` 的名字，並確認它只在伺服器端程式使用：\n"
                                f"1. 要改：`{f.path}` 與所有用到這個變數的地方；部署平台上的環境變數名一起改。\n"
                                f"2. 瀏覽器端改用 anon / publishable key。\n"
                                f"3. 不可以動到：資料表與 RLS 設定。\n"
                                f"4. 驗證：`npm run build` 後在 `.next/static` 裡搜尋不到這把金鑰的值。"),
                    rule_id="database.next_public_secret", file_path=f.path, line=i,
                    fingerprint_key=m.group(0),
                ))
        if _is_frontend(f.path, f.text):
            for i, line in enumerate(f.lines, 1):
                if _SERVICE_REF_RE.search(line) and not _NEXT_PUBLIC_SECRET_RE.search(line):
                    out.append(Finding(
                        category="database", severity="critical",
                        title=f"前端檔案 {f.name} 用到 service role key",
                        plain_explanation=(f"`{f.path}` 是會跑在使用者瀏覽器裡的檔案，卻提到了 service role key。"
                                           f"這把鑰匙可以略過所有資料表的鎖，放在前端等於把總鑰匙交出去。"),
                        advanced_explanation=f"`{f.path}:{i}` 在前端檔案中參照 service role。這把 key 只能存在伺服器端。",
                        fix_prompt=(f"`{f.path}` 第 {i} 行在前端用到 service role key，請改成：\n"
                                    f"1. 要改：需要高權限的操作搬到伺服器端（API route / 後端 route），前端只呼叫那支 API。\n"
                                    f"2. 前端只能用 anon / publishable key。\n"
                                    f"3. 不可以動到：資料表結構、RLS。\n"
                                    f"4. 驗證：在所有前端檔案搜尋 `service_role` 沒有結果。"),
                        rule_id="database.service_role_frontend", file_path=f.path, line=i,
                        fingerprint_key=line.strip()[:80],
                    ))
                    break

    # ── 資料表沒開 RLS ──
    sql_files = [f for f in proj.files if f.ext == ".sql" and f.text]
    if not sql_files:
        out.append(Finding(
            category="database", severity="medium",
            title="找不到資料表定義，無法確認有沒有上鎖",
            plain_explanation=("這個專案有用 Supabase，但專案裡找不到建立資料表的 SQL 檔。"
                               "所以這次沒辦法幫你確認資料表有沒有開「Row Level Security（列層級鎖）」，"
                               "請到 Supabase 後台看一下每張表旁邊有沒有顯示 RLS enabled。"),
            advanced_explanation="沒有 *.sql（migration / schema）。RLS 狀態只能從線上資料庫確認。",
            fix_prompt=("請幫我把 Supabase 的資料表結構匯出成 `migrations/` 底下的 SQL 檔，讓之後的健檢看得到：\n"
                        "1. 要改：新增 `migrations/000_schema.sql`，內容是目前所有資料表的 CREATE TABLE 與 RLS 設定（可以用 Supabase CLI 的 `supabase db dump --schema public`）。\n"
                        "2. 不可以動到：線上資料庫本身，這一步只讀不寫。\n"
                        "3. 驗證：檔案裡每張表都有對應的 `ENABLE ROW LEVEL SECURITY`；沒有的話列給我看。"),
            rule_id="database.no_schema",
        ))
        return out

    created: dict[str, str] = {}     # table -> 第一個建立它的檔案
    enabled: set[str] = set()
    dynamic_files: list[str] = []
    for f in sorted(sql_files, key=lambda x: x.path):
        sql = _COMMENT_RE.sub(" ", f.text)
        for m in _CREATE_RE.finditer(sql):
            schema_m = _CREATE_SCHEMA_RE.match(sql, m.start())
            if schema_m and schema_m.group(1).lower() != "public":
                continue   # auth.*、storage.* 等不是我們的表
            created.setdefault(m.group(1).lower(), f.path)
        enabled |= {m.group(1).lower() for m in _ENABLE_RE.finditer(sql)}
        for m in _DISABLE_RE.finditer(sql):
            enabled.discard(m.group(1).lower())
        for m in _DROP_RE.finditer(sql):
            created.pop(m.group(1).lower(), None)
        if _DYNAMIC_ENABLE_RE.search(sql):
            dynamic_files.append(f.path)

    missing = sorted(t for t in created if t not in enabled)
    if missing and not dynamic_files:
        first_file = created[missing[0]]
        shown = "、".join(f"`{t}`" for t in missing[:8]) + (f" 等 {len(missing)} 張表" if len(missing) > 8 else "")
        out.append(Finding(
            category="database", severity="critical",
            title=f"{len(missing)} 張資料表沒有上鎖",
            plain_explanation=(f"{shown} 在 SQL 檔裡沒有開「Row Level Security（列層級鎖）」。"
                               f"沒上鎖的表，只要有人拿到你的 Supabase 網址和公開金鑰（anon key，前端本來就看得到），"
                               f"就能直接讀、甚至改裡面的資料。"),
            advanced_explanation=(f"在 {len(sql_files)} 個 SQL 檔中找到 {len(created)} 張 public 表，"
                                  f"其中 {len(missing)} 張沒有 `ALTER TABLE … ENABLE ROW LEVEL SECURITY`。"
                                  f"注意：這只看 migration 檔；若已在 Supabase 後台手動開啟，請以後台為準。"),
            fix_prompt=("請幫我新增一個 migration 檔，替以下資料表開啟 RLS：\n"
                        + "\n".join(f"- {t}" for t in missing) + "\n"
                        "1. 要改：新增 `migrations/` 底下一個新的 SQL 檔，每張表一行 `ALTER TABLE public.<表名> ENABLE ROW LEVEL SECURITY;`。\n"
                        "2. 先確認伺服器端是用 service role key 存取（那會略過 RLS，功能不受影響）；"
                        "如果有前端直接用 anon key 讀寫某張表，先列給我看，那張表要另外寫 policy，不要直接鎖死。\n"
                        "3. 不可以動到：既有的 migration 檔、資料本身。\n"
                        "4. 驗證：在 Supabase 後台每張表都顯示 RLS enabled；用 anon key 查詢這些表拿不到資料。"),
            rule_id="database.rls_disabled", file_path=first_file,
            fingerprint_key="rls",
            extra={"tables": missing},
        ))
    return out
