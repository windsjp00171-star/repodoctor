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
