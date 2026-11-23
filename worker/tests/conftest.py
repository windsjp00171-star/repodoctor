"""測試用的假專案在 tmp 資料夾裡現場組出來。

假金鑰一律用字串拼接產生，不整串寫在原始碼裡——不然本工具掃自己會報警，GitHub 也會。
"""
import subprocess
import textwrap

import pytest

FAKE = {
    "anthropic": "sk-" + "ant-api03-" + "Zq8" * 15,
    "groq": "gsk_" + "Vb7Kp2Lm9Qx4" * 4,
    "service_role_jwt": None,  # 下面組
    "dropbox": "m1" + "09xq" + "7Hc2Lp" * 2,
}


def _jwt(role: str) -> str:
    import base64, json
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return enc({"alg": "HS256", "typ": "JWT"}) + "." + enc({"iss": "supabase", "role": role}) + "." + "Sg9" * 12


FAKE["service_role_jwt"] = _jwt("service_role")
FAKE["anon_jwt"] = _jwt("anon")


def write(root, files: dict):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def git_init(root, commit=True):
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)
    run("init", "-q")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    if commit:
        run("add", "-A")
        run("commit", "-qm", "init")


@pytest.fixture
def leaky_flask(tmp_path):
    """一個什麼問題都有的 Flask + Supabase 專案。"""
    write(tmp_path, {
        "requirements.txt": "flask\nsupabase\n",
        "db.py": """
            import os
            from supabase import create_client
            supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        """,
        "config.py": f"""
            ANTHROPIC_KEY = "{FAKE['anthropic']}"
            SUPABASE_SERVICE = "{FAKE['service_role_jwt']}"
            PUBLIC_ANON = "{FAKE['anon_jwt']}"
            DROPBOX_APP_SECRET = "{FAKE['dropbox']}"
            TOKEN_URL = "https://oauth2.googleapis.com/token"
        """,
        "routes/admin.py": """
            from flask import Blueprint, session, request
            from supabase import create_client
            bp = Blueprint("admin", __name__)
            sb = create_client("u", "k")

            def login_required(f):
                return f

            @bp.route("/admin/users")
            def users():
                password = request.form["password"]
                return "ok"
        """,
        "routes/public.py": """
            def login_required(f):
                return f
        """,
        "migrations/001.sql": """
            create table if not exists public.members (id uuid primary key);
            create table orders (id int);
            -- create table commented_out (id int);
            create table auth.not_ours (id int);
            alter table orders enable row level security;
        """,
        "static/app.js": "const k = process.env.SUPABASE_SECRET_KEY;\n",
        ".env": f"GROQ_API_KEY={FAKE['groq']}\n",
        "README.md": "# demo\n",
        ".gitignore": "__pycache__/\n",
    })
    git_init(tmp_path)
    return tmp_path
