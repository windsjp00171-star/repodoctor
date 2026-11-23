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
