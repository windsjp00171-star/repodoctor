"""規則掃描：該抓的要抓到（緊急零漏抓），不該抓的不要抓（假警報）。"""
import json
import subprocess

from cli import scan
from scanner.files import load_project
from scanner.rules import candidates, hygiene, secrets, supabase_rls
from scanner.secret_patterns import detect
from tests.conftest import FAKE, git_init, write


def _rules(findings):
    return [(f.rule_id, f.file_path, f.severity) for f in findings]


# ── 金鑰外洩 ──

def test_catches_known_format_and_named_secrets(leaky_flask):
    fs = secrets.scan(load_project(leaky_flask))
    hits = {(f.file_path, f.line) for f in fs if f.rule_id == "secrets.in_file"}
    assert ("config.py", 1) in hits          # Anthropic
    assert ("config.py", 2) in hits          # service role JWT
    assert ("config.py", 4) in hits          # DROPBOX_APP_SECRET（沒有已知格式，靠變數名）
    assert all(f.severity == "critical" for f in fs if f.file_path == "config.py")


def test_does_not_flag_anon_key_urls_or_code_expressions(leaky_flask):
    fs = secrets.scan(load_project(leaky_flask))
    lines = {(f.file_path, f.line) for f in fs}
    assert ("config.py", 3) not in lines      # anon key 本來就是公開的
    assert ("config.py", 5) not in lines      # TOKEN_URL 是網址
    assert not any(f.file_path == "routes/admin.py" for f in fs)   # password = request.form[...]


def test_gitignored_env_is_not_a_leak_but_committed_env_is(tmp_path):
    write(tmp_path, {".env": f"GROQ_API_KEY={FAKE['groq']}\n", ".gitignore": ".env\n", "a.py": "x=1\n"})
    git_init(tmp_path)
    assert secrets.scan(load_project(tmp_path)) == []

    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", ".env"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "oops"], check=True)
    fs = secrets.scan(load_project(tmp_path))
    assert [(f.file_path, f.severity) for f in fs] == [(".env", "critical")]


def test_uncommitted_secret_is_high_not_critical(tmp_path):
    write(tmp_path, {"a.py": "x=1\n"})
    git_init(tmp_path)
    write(tmp_path, {"new.py": f'KEY = "{FAKE["anthropic"]}"\n'})
    fs = secrets.scan(load_project(tmp_path))
    assert [(f.file_path, f.severity) for f in fs] == [("new.py", "high")]


def test_env_file_deleted_but_still_in_history(tmp_path):
    write(tmp_path, {".env": "A=1\n", "a.py": "x=1\n"})
    git_init(tmp_path)
    subprocess.run(["git", "-C", str(tmp_path), "rm", "-q", ".env"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "rm"], check=True)
    fs = secrets.scan(load_project(tmp_path))
    assert [(f.rule_id, f.severity) for f in fs] == [("secrets.in_history", "critical")]


def test_env_example_blank_values_do_not_swallow_next_line():
    # 曾經的 bug：`LINE_SECRET=` 後面是換行，正規表示式把下一行的網址當成值
    text = "LINE_CHANNEL_SECRET=\nLINE_REDIRECT_URI=https://my-church.onrender.com/auth/callback2\n"
    assert detect(text, allow_unquoted=True) == []


def test_teaching_fakes_are_not_flagged():
    assert detect('apiKey: "sk-proj-7890abcdef1234567890"') == []
    assert detect("const s = '0123456789abcdef0123456789abcdef';") == []


# ── 資料庫權限 ──

def test_rls_missing_tables(leaky_flask):
    fs = supabase_rls.scan(load_project(leaky_flask))
    rls = [f for f in fs if f.rule_id == "database.rls_disabled"]
    assert len(rls) == 1 and rls[0].severity == "critical"
    assert rls[0].extra["tables"] == ["members"]   # orders 有開；註解裡的、auth.* 不算


def test_dynamic_enable_all_counts_as_enabled(tmp_path):
    write(tmp_path, {"requirements.txt": "supabase\n", "m.sql": """
        create table a (id int);
        do $$ declare r record; begin for r in select tablename from pg_tables loop
          execute format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', r.tablename);
        end loop; end $$;
    """})
    assert supabase_rls.scan(load_project(tmp_path)) == []


def test_service_role_in_frontend(leaky_flask):
    fs = supabase_rls.scan(load_project(leaky_flask))
    assert ("database.service_role_frontend", "static/app.js", "critical") in _rules(fs)


def test_not_supabase_project_skips_database_checks(tmp_path):
    write(tmp_path, {"README.md": "我們以後可能會用 supabase\n", "m.sql": "create table a (id int);\n"})
    assert supabase_rls.scan(load_project(tmp_path)) == []


# ── 重複與散落 ──

def test_db_client_outside_db_py_and_duplicate_guards(leaky_flask):
    fs, _ = candidates.scan(load_project(leaky_flask))
    by_rule = {f.rule_id: f for f in fs}
    assert by_rule["duplication.db_client"].extra["sites"] == [{"file": "routes/admin.py", "line": 4}]
    assert "login_required" in by_rule["duplication.guard"].title


def test_single_client_file_is_the_central_place(tmp_path):
    write(tmp_path, {"package.json": '{"dependencies":{"@supabase/supabase-js":"2"}}',
                     "lib/supabase.js": "import { createClient } from '@supabase/supabase-js'\nexport const s = createClient(a, b)\n"})
    fs, _ = candidates.scan(load_project(tmp_path))
    assert fs == []


def test_create_client_in_strings_is_not_a_call(tmp_path):
    write(tmp_path, {"requirements.txt": "supabase\n", "db.py": "x=1\n",
                     "help.py": 'MSG = "請搜尋 create_client( 只剩一處"\n# create_client(\n'})
    fs, _ = candidates.scan(load_project(tmp_path))
    assert fs == []


# ── 專案衛生 ──

def test_hygiene(tmp_path):
    write(tmp_path, {"app.py": "import os\nos.environ.get('X')\n" + "x = 1\n" * 1200, "app_copy.py": "x=1\n"})
    ids = {f.rule_id for f in hygiene.scan(load_project(tmp_path))}
    assert {"hygiene.no_readme", "hygiene.no_gitignore", "hygiene.long_file", "hygiene.dead_file"} <= ids


# ── 報告 ──

def test_report_never_contains_full_secret(leaky_flask):
    text = json.dumps(scan(str(leaky_flask), use_ai=False), ensure_ascii=False)
    for name, v in FAKE.items():
        assert v not in text, name
        if name != "anon_jwt":
            assert v[:4] + "…" in text, name   # 只留前 4 碼（.env 在這個假專案裡有被 commit）


def test_fingerprint_ignores_line_numbers(leaky_flask):
    before = {f["fingerprint"] for f in scan(str(leaky_flask), use_ai=False)["findings"]}
    p = leaky_flask / "config.py"
    p.write_text("# 加一行\n" + p.read_text())
    after = {f["fingerprint"] for f in scan(str(leaky_flask), use_ai=False)["findings"]}
    assert before == after


def test_no_ai_marks_ai_categories_as_not_scored(leaky_flask):
    r = scan(str(leaky_flask), use_ai=False)
    assert r["category_scores"]["auth"] is None and r["category_scores"]["drift"] is None
    assert r["score"] <= 59   # 有緊急問題
    assert r["token_usage"]["total"]["cost_usd"] == 0
