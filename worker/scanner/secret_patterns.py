"""疑似金鑰的偵測：只有這一份。`rules/secrets.py`（報告）和 `masking.py`（送 AI 前）都用它。

兩種信心：
- confident：已知格式、或「變數名像金鑰 ＋ 值像金鑰」。報告只報這一種。
- loose：高熵長字串。只用在送 AI 前多遮一層，不報告（假警報太多）。
"""
from __future__ import annotations

import base64
import json
import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Secret:
    start: int
    end: int
    value: str
    kind: str          # 給人看的種類名稱
    provider: str      # 到哪裡作廢這把金鑰
    env_name: str      # 建議的環境變數名
    confident: bool
    severity: str = "critical"


# (kind, provider, env_name, severity, regex)
_KNOWN = [
    ("Anthropic API key", "Anthropic Console", "ANTHROPIC_API_KEY", "critical",
     r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("OpenAI API key", "OpenAI 後台", "OPENAI_API_KEY", "critical",
     r"sk-(?:proj-|svcacct-)?(?!ant-)[A-Za-z0-9_\-]{32,}"),
    ("Groq API key", "Groq Console", "GROQ_API_KEY", "critical",
     r"gsk_[A-Za-z0-9]{40,}"),
    # Google API key 有些是設計上公開的（Maps、YouTube 網頁自帶的 key），所以是 high 不是 critical
    ("Google API key", "Google Cloud Console", "GOOGLE_API_KEY", "high",
     r"AIza[0-9A-Za-z_\-]{35}"),
    ("Google OAuth client secret", "Google Cloud Console", "GOOGLE_CLIENT_SECRET", "high",
     r"GOCSPX-[A-Za-z0-9_\-]{28}"),
    ("GitHub token", "GitHub 設定 → Developer settings", "GITHUB_TOKEN", "critical",
     r"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})"),
    ("AWS access key", "AWS IAM", "AWS_ACCESS_KEY_ID", "critical",
     r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    ("Stripe secret key", "Stripe 後台", "STRIPE_SECRET_KEY", "critical",
     r"(?:sk|rk)_live_[A-Za-z0-9]{20,}"),
    ("Slack token", "Slack App 設定", "SLACK_TOKEN", "critical",
     r"xox[baprs]-[A-Za-z0-9\-]{20,}"),
    ("Supabase secret key", "Supabase 後台 → Project Settings → API Keys", "SUPABASE_SECRET_KEY", "critical",
     r"sb_secret_[A-Za-z0-9_\-]{20,}"),
    ("私鑰", "產生這把私鑰的地方（重新產生一把）", "PRIVATE_KEY", "critical",
     r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"),
]
_KNOWN_RE = [(k, p, e, s, re.compile(rx)) for k, p, e, s, rx in _KNOWN]

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")

# 變數名像金鑰：FOO_SECRET = "..."、"apiKey": "..."、TOKEN=... （.env 沒引號）
_NAME = r"[A-Za-z0-9_]*(?:SECRET|TOKEN|API_?KEY|APIKEY|PASSWORD|PASSWD|PRIVATE_?KEY|ACCESS_?KEY|CLIENT_?SECRET|AUTH_?KEY|SERVICE_?ROLE)[A-Za-z0-9_]*"
_ASSIGN_RE = re.compile(
    r"""(?ix)
    (?P<name>""" + _NAME + r""")["']?
    [ \t]*(?::|=|:=|=>)[ \t]*
    (?P<q>["'`]?)
    (?P<val>[^\s"'`,;)\]}]{8,})
    (?P=q)
    """
)

_PLACEHOLDER_RE = re.compile(
    r"(?i)^(?:x{4,}|\*{3,}|\.{3,}|<.*>|\{\{.*\}\}|\$\{.*\}|%\(.*|"
    r".*(?:your|example|sample|placeholder|changeme|change_me|dummy|fake|test|replace|todo|here|"
    r"xxx|\.\.\.|process\.env|os\.environ|os\.getenv|environ|getenv|config\.|settings\.|import\.meta).*)$"
)
_LOOSE_RE = re.compile(r"(?<![A-Za-z0-9_\-+=])[A-Za-z0-9_\-+=]{24,}(?![A-Za-z0-9_\-+=])")


def entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())


_SEQUENTIAL_RE = re.compile(r"(?i)0123456|1234567|2345678|3456789|abcdef|qwerty|deadbeef")


def _looks_secret(val: str) -> bool:
    if _PLACEHOLDER_RE.match(val) or _SEQUENTIAL_RE.search(val):
        return False   # 教學範例、測試用的假值（1234567890、abcdef…）
    if re.match(r"[A-Za-z_][\w.]*[\[(]", val):
        return False  # 程式運算式（request.form[...]、os.getenv(...)），不是值
    if re.fullmatch(r"https?://\S+", val) and "@" not in val:
        return False
    has_digit, has_alpha = bool(re.search(r"\d", val)), bool(re.search(r"[A-Za-z]", val))
    if has_digit and has_alpha and len(val) >= 10 and entropy(val) >= 3.0:
        return True
    return len(val) >= 32 and entropy(val) >= 4.0


def _jwt_role(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("role")
    except Exception:
        return None


def _env_name_from(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", re.sub(r"([a-z])([A-Z])", r"\1_\2", name)).upper().strip("_")


def detect(text: str, include_loose: bool = False, allow_unquoted: bool = False) -> list[Secret]:
    """找出 text 裡所有疑似金鑰。重疊時保留先找到的（已知格式優先）。

    allow_unquoted：只有 .env / 設定檔才接受沒有引號的值。程式碼裡沒有引號的
    右邊幾乎都是變數或運算式（`token = data.get(...)`），算進來假警報會很多。
    """
    found: list[Secret] = []

    def add(s: Secret):
        for f in found:
            if s.start < f.end and f.start < s.end:
                return
        found.append(s)

    for kind, provider, env, sev, rx in _KNOWN_RE:
        for m in rx.finditer(text):
            add(Secret(m.start(), m.end(), m.group(0), kind, provider, env, True, sev))

    for m in _JWT_RE.finditer(text):
        role = _jwt_role(m.group(0))
        if role == "service_role":
            add(Secret(m.start(), m.end(), m.group(0), "Supabase service role key",
                       "Supabase 後台 → Project Settings → API", "SUPABASE_SERVICE_ROLE_KEY", True))
        elif include_loose:
            # anon key 本來就是公開的，不報告；但送 AI 時一樣遮掉
            add(Secret(m.start(), m.end(), m.group(0), "JWT", "", "", False))

    for m in _ASSIGN_RE.finditer(text):
        val = m.group("val")
        if not m.group("q") and not allow_unquoted:
            continue
        if _looks_secret(val):
            add(Secret(m.start("val"), m.end("val"), val, f"寫死的 {m.group('name')}",
                       "發這把金鑰的服務後台", _env_name_from(m.group("name")), True))

    if include_loose:
        for m in _LOOSE_RE.finditer(text):
            v = m.group(0)
            if re.search(r"[A-Za-z]", v) and re.search(r"\d", v) and entropy(v) >= 4.0 \
                    and not re.fullmatch(r"[a-z0-9_]+", v):
                add(Secret(m.start(), m.end(), v, "高熵字串", "", "", False))

    return sorted(found, key=lambda s: s.start)
