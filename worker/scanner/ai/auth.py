"""AI 檢查：登入與權限。

規則先把「路由」和「全域保護」挑出來，只送這些片段，不送整個 repo。
全域保護（before_request、middleware、decorator 定義）每一次請求都會帶上——
少了它，模型會把有被全域擋住的路由誤判成「沒登入也能進」。
"""
from __future__ import annotations

import re

import config
from scanner.ai.client import AIClient, AICheckError
from scanner.ai.common import FINDINGS_SCHEMA, WRITING_RULES, coverage, numbered, pack, to_findings
from scanner.files import FileInfo, Project
from scanner.masking import Masker
from scanner.rules.candidates import _is_test

_FLASK_ROUTE_RE = re.compile(r"^\s*@[\w.]+\.(?:route|get|post|put|delete|patch)\s*\(")
_FLASK_GLOBAL_RE = re.compile(r"^\s*@[\w.]+\.(?:before_request|before_app_request)\b")
_DECORATOR_RE = re.compile(r"^\s*@")
_PY_GUARD_DEF_RE = re.compile(r"^def\s+(\w*(?:required|require_\w+|permission\w*|_guard)\w*)\s*\(")
_DJANGO_VIEW_RE = re.compile(r"^(?:def\s+\w+\s*\(\s*request\b|class\s+\w+\(.*View.*\)\s*:)")
_EXPRESS_RE = re.compile(r"\b(?:app|router)\.(?:get|post|put|delete|patch|all|use)\s*\(")
# Next.js route handler、pages/api、Vercel serverless（api/*.js）
_NEXT_ROUTE_RE = re.compile(r"(^|/)(app/.*route\.[jt]s|pages/api/.*\.[jt]sx?)$|^api/.*\.[jt]s$")
_NEXT_SENSITIVE_PAGE_RE = re.compile(r"(^|/)app/.*(admin|dashboard|account|settings|staff|manage)[^/]*/.*page\.[jt]sx$")
_MIDDLEWARE_RE = re.compile(r"(^|/)(src/)?middleware\.[jt]s$|(^|/)middleware\.py$")

SYSTEM = """你是一位資安審查員，幫不會寫程式的人檢查他們的 web 專案「登入與權限」有沒有漏洞。

你會收到：
1. 全域保護：before_request、middleware、權限 decorator 的定義（每次都會附上）
2. 路由片段：每個路由的 decorator、函式開頭

要找的問題：
- 應該要登入／要權限的路由，卻沒有任何保護（沒有 decorator、函式開頭也沒檢查、全域保護也沒涵蓋）
- 一般使用者能進管理功能（例如 /admin、/staff 的路由只檢查有登入、沒檢查身分）
- 權限檢查各寫各的：有統一的 decorator，某些路由卻在函式裡手寫 `if not session...`，容易漏改
- decorator 順序錯誤，導致保護沒有生效（例如 Flask 的 @login_required 寫在 @app.route 上面）

不要報的：
- 本來就該公開的頁面：首頁、登入、登出、OAuth callback、健康檢查、靜態檔、公開的報名表單、manifest、robots
- 被全域保護（before_request / middleware）已經擋住的路由
- 你只看到片段、無法確定的——那種請把 confidence 填 low

""" + WRITING_RULES


def _decorated_block(lines: list[str], i: int, body: int) -> tuple[int, int]:
    """以第 i 行（0 起算）的 decorator 為中心，往上找連續 decorator，往下包含 def 與前 body 行。"""
    start = i
    while start > 0 and _DECORATOR_RE.match(lines[start - 1]):
        start -= 1
    j = i
    while j < len(lines) and not re.match(r"^\s*(async\s+)?def\s", lines[j]):
        j += 1
    return start + 1, min(len(lines), j + 1 + body)


def _func_block(lines: list[str], i: int, max_lines: int = 60) -> tuple[int, int]:
    start, indent = i, len(lines[i]) - len(lines[i].lstrip())
    while start > 0 and _DECORATOR_RE.match(lines[start - 1]):
        start -= 1
    end = i + 1
    while end < len(lines) and end - i < max_lines:
        ln = lines[end]
        if ln.strip() and len(ln) - len(ln.lstrip()) <= indent and not ln.lstrip().startswith((")", "#")):
            break
        end += 1
    return start + 1, end


def collect(proj: Project) -> tuple[list[str], list[tuple[str, str]]]:
    """回傳 (全域保護片段, 路由片段)。"""
    context: list[str] = []
    units: list[tuple[str, str]] = []
    files: list[FileInfo] = [f for f in proj.code_files() if not _is_test(f.path)]
    for f in files:
        lines = f.lines
        if _MIDDLEWARE_RE.search(f.path):
            context.append(numbered(f.path, lines, 1, min(len(lines), 150)))
            continue
        if f.ext == ".py":
            seen_until = 0
            for i, ln in enumerate(lines):
                if i < seen_until:
                    continue
                if _FLASK_GLOBAL_RE.match(ln):
                    s, e = _func_block(lines, i + 1 if i + 1 < len(lines) else i)
                    context.append(numbered(f.path, lines, s, e))
                    seen_until = e
                elif _PY_GUARD_DEF_RE.match(ln):
                    s, e = _func_block(lines, i)
                    context.append(numbered(f.path, lines, s, e))
                    seen_until = e
                elif _FLASK_ROUTE_RE.match(ln):
                    s, e = _decorated_block(lines, i, body=12)
                    units.append((f.path, numbered(f.path, lines, s, e)))
                    seen_until = e
                elif f.name == "views.py" and _DJANGO_VIEW_RE.match(ln):
                    s, e = _decorated_block(lines, i, body=10) if i and _DECORATOR_RE.match(lines[i - 1]) else (i + 1, min(len(lines), i + 11))
                    units.append((f.path, numbered(f.path, lines, s, e)))
                    seen_until = e
            if f.name == "urls.py":
                units.append((f.path, numbered(f.path, lines, 1, min(len(lines), 150))))
        else:
            if _NEXT_ROUTE_RE.search(f.path) or _NEXT_SENSITIVE_PAGE_RE.search(f.path):
                units.append((f.path, numbered(f.path, lines, 1, min(len(lines), 40))))
                continue
            for i, ln in enumerate(lines):
                if _EXPRESS_RE.search(ln):
                    units.append((f.path, numbered(f.path, lines, i + 1, min(len(lines), i + 9))))
    return context, units


def run(proj: Project, ai: AIClient, masker: Masker) -> tuple[list, dict]:
    context, units = collect(proj)
    if not units:
        return [], {"status": "not_applicable", "note": "找不到路由（不是 web 專案，或用了不認得的框架）"}

    context = [masker.mask(c) for c in context]
    units = [(p, masker.mask(t)) for p, t in units]
    requests, skipped = pack(context, units, config.max_input_chars("auth"), config.MAX_CALLS_PER_CHECK)

    ctx_text = "\n\n".join(context) or "（沒有找到 before_request / middleware / 權限 decorator）"
    findings, dropped, errors, ok = [], {"low_confidence": 0, "unknown_file": 0}, [], 0
    for body, sent_files in requests:
        prompt = ("以下是這個專案的全域保護與路由片段。請找出登入與權限的問題。\n\n"
                  "【全域保護】\n" + ctx_text + "\n\n【路由】\n" + body)
        try:
            data = ai.ask("auth", SYSTEM, prompt, FINDINGS_SCHEMA)
        except AICheckError as e:
            errors.append(str(e))
            break
        ok += 1
        fs, d = to_findings(data, "auth", "ai.auth", sent_files)
        findings += fs
        for k in d:
            dropped[k] += d[k]

    return findings, coverage(ok, errors, len(units), skipped, dropped,
                              f"送出 {len(units) - skipped}/{len(units)} 個路由片段、{len(context)} 段全域保護")
