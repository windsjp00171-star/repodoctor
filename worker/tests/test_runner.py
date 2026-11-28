"""雲端 worker：授權判斷與程式碼處理。"""
import subprocess

import pytest

import github_app
import runner


class FakeTable:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.filters = db, name, None, None, []

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def upsert(self, payload, **kw):
        self.op, self.payload = "upsert", payload
        return self

    def eq(self, k, v):
        self.filters.append((k, v))
        return self

    def execute(self):
        self.db.calls.append((self.name, self.op, self.payload, self.filters))
        return type("R", (), {"data": []})()


class FakeDB:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return FakeTable(self, name)


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(runner, "supabase", db)
    return db


ROW = {"id": "inst-1", "user_id": "user-1", "github_installation_id": 42}


def test_installation_of_someone_else_is_rejected(fake_db, monkeypatch):
    monkeypatch.setattr(github_app, "get_installation", lambda i: {"account_login": "stranger", "account_type": "User"})
    monkeypatch.setattr(runner, "github_login_of", lambda uid: "me")
    monkeypatch.setattr(github_app, "list_repos", lambda i: pytest.fail("不該去拉別人的 repo 清單"))
    runner.verify_installation(ROW)
    assert fake_db.calls[0][1] == "update" and fake_db.calls[0][2]["status"] == "rejected"
    assert not any(c[0] == "repos" for c in fake_db.calls)


def test_own_installation_is_activated_and_repos_synced(fake_db, monkeypatch):
    monkeypatch.setattr(github_app, "get_installation", lambda i: {"account_login": "Me", "account_type": "User"})
    monkeypatch.setattr(runner, "github_login_of", lambda uid: "me")
    monkeypatch.setattr(github_app, "list_repos", lambda i: [{"github_repo_id": 1, "full_name": "me/app",
                                                              "default_branch": "main", "language": "Python"}])
    runner.verify_installation(ROW)
    assert ("installations", "update") == fake_db.calls[0][:2] and fake_db.calls[0][2]["status"] == "active"
    repos = next(c for c in fake_db.calls if c[0] == "repos")[2]
    assert repos[0]["user_id"] == "user-1" and repos[0]["installation_id"] == "inst-1"


def test_user_without_github_identity_is_rejected(fake_db, monkeypatch):
    monkeypatch.setattr(github_app, "get_installation", lambda i: {"account_login": "me", "account_type": "User"})
    monkeypatch.setattr(runner, "github_login_of", lambda uid: None)
    runner.verify_installation(ROW)
    assert fake_db.calls[0][2]["status"] == "rejected"


def test_clone_keeps_token_out_of_url_and_disk(monkeypatch, tmp_path):
    token = "ghs_" + "Tk9" * 12
    monkeypatch.setattr(github_app, "installation_token", lambda i: token)
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(github_app.subprocess, "run", fake_run)
    github_app.shallow_clone(42, "me/app", str(tmp_path / "r"))
    url = next(a for a in seen["cmd"] if a.startswith("https://"))
    assert token not in url and "@" not in url        # 不進網址 → 不會寫進 .git/config
    assert "--depth" in seen["cmd"]
    assert not any(token in a for a in seen["cmd"])   # header 裡是 base64，原值也不出現在指令列


class FakeQuery:
    def __init__(self, data):
        self.data = data

    def select(self, *a, **k):
        return self

    @property
    def not_(self):  # 真的 postgrest client 上 not_ 是 property，不是方法
        return self

    def __getattr__(self, name):
        return lambda *a, **k: self

    def execute(self):
        return type("R", (), {"data": self.data})()


def test_deletion_requests_delete_auth_users(monkeypatch):
    deleted = []

    class DB:
        auth = type("A", (), {"admin": type("Adm", (), {"delete_user": staticmethod(lambda uid: deleted.append(uid))})()})()

        def table(self, name):
            assert name == "profiles"
            return FakeQuery([{"id": "u1"}, {"id": "u2"}])
    monkeypatch.setattr(runner, "supabase", DB())
    runner.process_deletion_requests()
    assert deleted == ["u1", "u2"]


def test_one_failed_deletion_does_not_stop_the_others(monkeypatch):
    deleted = []

    def delete_user(uid):
        if uid == "u1":
            raise RuntimeError("boom")
        deleted.append(uid)

    class DB:
        auth = type("A", (), {"admin": type("Adm", (), {"delete_user": staticmethod(delete_user)})()})()

        def table(self, name):
            return FakeQuery([{"id": "u1"}, {"id": "u2"}])
    monkeypatch.setattr(runner, "supabase", DB())
    runner.process_deletion_requests()
    assert deleted == ["u2"]


def test_purge_uses_configured_retention(monkeypatch):
    import config
    calls = []

    class DB:
        def rpc(self, fn, params):
            calls.append((fn, params))
            return FakeQuery(0)
    monkeypatch.setattr(runner, "supabase", DB())
    runner.purge_expired()
    assert calls == [("purge_expired_findings", {"retention_days": config.RETENTION_DAYS})]


def test_privacy_jobs_failing_does_not_stop_scans(monkeypatch):
    def boom():
        raise RuntimeError("column delete_requested_at does not exist")
    monkeypatch.setattr(runner, "process_deletion_requests", boom)
    monkeypatch.setattr(runner, "purge_expired", boom)
    monkeypatch.setattr(runner, "sync_active_installations", boom)
    monkeypatch.setattr(runner, "process_installations", lambda: None)
    scanned = []
    monkeypatch.setattr(runner, "process_scan", scanned.append)

    class DB:
        def rpc(self, fn, *a):
            return FakeQuery([{"id": "s1"}])
    monkeypatch.setattr(runner, "supabase", DB())
    assert runner.tick() is True and scanned == [{"id": "s1"}]


def test_repos_added_later_are_synced(monkeypatch):
    """第一次安裝後再到 GitHub 加 repo：已經 active 的安裝也要重拉清單。"""
    upserts = []

    class Q(FakeQuery):
        def upsert(self, payload, **kw):
            upserts.append(payload)
            return self

    class DB:
        def table(self, name):
            return Q([ROW | {"status": "active"}])
    monkeypatch.setattr(runner, "supabase", DB())
    monkeypatch.setattr(github_app, "list_repos", lambda i: [
        {"github_repo_id": 1, "full_name": "me/old", "default_branch": "main", "language": None},
        {"github_repo_id": 2, "full_name": "me/new", "default_branch": "main", "language": None}])
    runner.sync_active_installations()
    assert [r["full_name"] for r in upserts[0]] == ["me/old", "me/new"]
    assert all(r["installation_id"] == "inst-1" and r["user_id"] == "user-1" for r in upserts[0])


def test_one_broken_installation_does_not_stop_sync(monkeypatch):
    upserts = []

    class Q(FakeQuery):
        def upsert(self, payload, **kw):
            upserts.append(payload)
            return self

    class DB:
        def table(self, name):
            return Q([ROW | {"id": "bad", "github_installation_id": 1}, ROW | {"id": "ok", "github_installation_id": 2}])

    def list_repos(i):
        if i == 1:
            raise github_app.GitHubError("uninstalled")
        return [{"github_repo_id": 3, "full_name": "me/x", "default_branch": "main", "language": None}]
    monkeypatch.setattr(runner, "supabase", DB())
    monkeypatch.setattr(github_app, "list_repos", list_repos)
    runner.sync_active_installations()
    assert len(upserts) == 1 and upserts[0][0]["installation_id"] == "ok"


def test_sync_records_time_and_survives_missing_column(monkeypatch):
    """同步完要記 repos_synced_at；那一欄還不存在（migration 005 沒跑）時，同步本身照樣成功。"""
    calls = []

    class Q(FakeQuery):
        def __init__(self, name):
            super().__init__([])
            self.name = name

        def upsert(self, payload, **kw):
            calls.append(("upsert", self.name))
            return self

        def update(self, payload):
            if "repos_synced_at" in payload:
                raise RuntimeError("column repos_synced_at does not exist")
            return self

    class DB:
        def table(self, name):
            return Q(name)
    monkeypatch.setattr(runner, "supabase", DB())
    monkeypatch.setattr(github_app, "list_repos", lambda i: [
        {"github_repo_id": 1, "full_name": "me/a", "default_branch": "main", "language": None}])
    runner.sync_repos(ROW)
    assert calls == [("upsert", "repos")]


# ── AI 誰能用（還沒串金流，AI 的錢是站長出的）──

class CountQuery(FakeQuery):
    """記下篩選條件；count 依「是不是只算 AI」「是不是只算這個人」回傳設定好的數字。"""
    def __init__(self, counts):
        super().__init__([])
        self.counts, self.ai, self.user = counts, False, False

    def eq(self, k, v):
        if k == "use_ai":
            self.ai = True
        if k == "user_id":
            self.user = True
        return self

    def execute(self):
        key = ("ai" if self.ai else "all") + ("_user" if self.user else "")
        return type("R", (), {"data": [], "count": self.counts.get(key, 0)})()


def _ai_env(monkeypatch, allow, counts=None):
    monkeypatch.setenv("GROQ_API_KEY", "test-" + "y" * 10)
    if allow is None:
        monkeypatch.delenv("AI_ALLOWLIST", raising=False)
    else:
        monkeypatch.setenv("AI_ALLOWLIST", allow)
    monkeypatch.setattr(runner, "github_login_of", lambda uid: "Me")

    class DB:
        def table(self, name):
            return CountQuery(counts or {})
    monkeypatch.setattr(runner, "supabase", DB())


SCAN = {"id": "s1", "user_id": "user-1", "use_ai": True}


def test_ai_is_closed_when_no_allowlist(monkeypatch):
    _ai_env(monkeypatch, None)
    ok, note = runner.ai_decision(SCAN)
    assert not ok and "受邀" in note


def test_ai_for_invited_login_case_insensitive(monkeypatch):
    _ai_env(monkeypatch, "someone, me")
    assert runner.ai_decision(SCAN) == (True, None)


def test_uninvited_user_gets_rules_only_with_reason(monkeypatch):
    _ai_env(monkeypatch, "someone-else")
    ok, note = runner.ai_decision(SCAN)
    assert not ok and "自己的金鑰" in note


def test_star_opens_ai_to_everyone(monkeypatch):
    _ai_env(monkeypatch, "*")
    monkeypatch.setattr(runner, "github_login_of", lambda uid: pytest.fail("開放給所有人時不用查帳號"))
    assert runner.ai_decision(SCAN)[0] is True


def test_per_user_ai_cap(monkeypatch):
    import config
    _ai_env(monkeypatch, "me", {"ai_user": config.AI_SCANS_PER_USER_PER_30_DAYS})
    ok, note = runner.ai_decision(SCAN)
    assert not ok and "30 天" in note


def test_global_ai_cap(monkeypatch):
    import config
    _ai_env(monkeypatch, "me", {"ai_user": 0, "ai": config.AI_SCANS_GLOBAL_PER_30_DAYS})
    ok, note = runner.ai_decision(SCAN)
    assert not ok and "全站" in note


def test_no_ai_requested_means_no_ai_and_no_note(monkeypatch):
    _ai_env(monkeypatch, "*")
    assert runner.ai_decision({**SCAN, "use_ai": False}) == (False, None)


def test_global_daily_cap_stops_scans(monkeypatch):
    """有人開很多帳號狂刷：全站每天的上限到了就不跑（保護 GitHub Actions 分鐘數）。"""
    import config
    failed = []
    repo = {"id": "r1", "user_id": "user-1", "full_name": "me/app",
            "installations": {"user_id": "user-1", "status": "active", "github_installation_id": 42}}

    class Scans(CountQuery):
        def update(self, payload):
            if payload.get("status") == "failed":
                failed.append(payload["error"])
            return self

    class DB:
        def table(self, name):
            if name == "repos":
                return FakeQuery(repo)
            return Scans({"all_user": 0, "all": config.GLOBAL_SCANS_PER_DAY})
    monkeypatch.setattr(runner, "supabase", DB())
    monkeypatch.setattr(github_app, "shallow_clone", lambda *a: pytest.fail("名額滿了不該下載程式碼"))
    runner.process_scan({"id": "s1", "user_id": "user-1", "repo_id": "r1", "use_ai": False})
    assert failed and "全站" in failed[0]


# ── 免登入秒檢 ──

class QuickDB:
    def __init__(self):
        self.updates = []

    def table(self, name):
        db = self

        class T(FakeQuery):
            def update(self, payload):
                db.updates.append((name, payload))
                return self
        return T([])


def test_quick_scan_writes_rule_only_report(monkeypatch, leaky_flask):
    import shutil as sh
    db = QuickDB()
    monkeypatch.setattr(runner, "supabase", db)
    monkeypatch.setattr(github_app, "public_shallow_clone",
                        lambda name, dest, timeout=0: sh.copytree(leaky_flask, dest))
    runner.process_quick_scan({"id": "q1", "full_name": "someone/app"})
    table, payload = db.updates[-1]
    assert table == "quick_scans" and payload["status"] == "done"
    assert payload["findings"] and all("fix_prompt" in f for f in payload["findings"])
    assert payload["coverage"]["auth"]["status"] == "skipped"          # 秒檢不跑 AI
    assert "秒檢" in payload["coverage"]["auth"]["note"]
    assert payload["meta"]["project"] == "someone/app"


def test_quick_scan_private_or_missing_repo_fails_with_reason(monkeypatch):
    db = QuickDB()
    monkeypatch.setattr(runner, "supabase", db)

    def boom(name, dest, timeout=0):
        raise github_app.GitHubError("找不到這個公開 repo")
    monkeypatch.setattr(github_app, "public_shallow_clone", boom)
    runner.process_quick_scan({"id": "q1", "full_name": "someone/private"})
    assert db.updates[-1][1]["status"] == "failed" and "公開" in db.updates[-1][1]["error"]


def test_quick_scan_rejects_huge_repo(monkeypatch, tmp_path):
    import config
    db = QuickDB()
    monkeypatch.setattr(runner, "supabase", db)
    monkeypatch.setattr(config, "QUICK_MAX_REPO_MB", 0)
    monkeypatch.setattr(github_app, "public_shallow_clone",
                        lambda name, dest, timeout=0: (__import__("os").makedirs(dest), open(dest + "/a.py", "w").write("x" * 10)))
    monkeypatch.setattr(runner, "run_scan", lambda *a, **k: pytest.fail("太大的 repo 不該健檢"))
    runner.process_quick_scan({"id": "q1", "full_name": "someone/huge"})
    assert db.updates[-1][1]["status"] == "failed" and "MB" in db.updates[-1][1]["error"]


def test_public_clone_never_sends_credentials(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["env"] = cmd, kw.get("env", {})
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(github_app.subprocess, "run", fake_run)
    monkeypatch.setattr(github_app, "installation_token", lambda i: pytest.fail("秒檢不可以拿 App 的權限"))
    github_app.public_shallow_clone("someone/app", str(tmp_path / "r"))
    joined = " ".join(seen["cmd"])
    assert "Authorization" not in joined and "credential.helper=" in joined
    assert seen["env"]["GIT_TERMINAL_PROMPT"] == "0"
