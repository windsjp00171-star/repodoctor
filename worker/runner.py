"""雲端 worker：輪詢 Supabase，處理兩種待辦。

1. 新的 GitHub 安裝（status = pending）
   → 向 GitHub 確認「這個安裝的帳號 = 這個使用者的 GitHub 帳號」，才標成 active 並同步 repo 清單。
   網站只能寫 installation id；真正的授權判斷在這裡，因為 worker 是唯一可信的一方。
2. 待做的健檢（status = queued）
   → 再驗一次權限 → 淺層 clone 到暫存資料夾 → 跑健檢 → 結果寫回 → **刪掉程式碼**。

    python runner.py            # 一直跑
    python runner.py --once     # 處理完目前的待辦就結束（測試用）
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone

import config
import github_app
from cli import scan as run_scan
from db import supabase

log = logging.getLogger("runner")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def github_login_of(user_id: str) -> str | None:
    """從 identities 讀（使用者自己改不到），不是從 user_metadata。"""
    user = supabase.auth.admin.get_user_by_id(user_id).user
    for ident in user.identities or []:
        if ident.provider == "github":
            return (ident.identity_data or {}).get("user_name")
    return None


# ── 1. 驗證新的安裝 ────────────────────────────────────────

def verify_installation(row: dict):
    try:
        info = github_app.get_installation(row["github_installation_id"])
        login = github_login_of(row["user_id"])
        if not login or not info["account_login"] or info["account_login"].lower() != login.lower():
            supabase.table("installations").update({
                "status": "rejected", "account_login": info.get("account_login"),
                "note": "這個 GitHub App 安裝不屬於你的 GitHub 帳號（目前只支援個人帳號，組織帳號之後再支援）",
            }).eq("id", row["id"]).execute()
            return
        supabase.table("installations").update({"status": "active", "account_login": info["account_login"], "note": None}) \
            .eq("id", row["id"]).execute()
        sync_repos(row)
    except github_app.GitHubError as e:
        supabase.table("installations").update({"status": "rejected", "note": str(e)}).eq("id", row["id"]).execute()


def sync_repos(row: dict):
    """把 GitHub 上「這個安裝可以讀的 repo」寫進 repos。只新增／更新，不刪：
    GitHub 偶爾回錯或回空的時候，不可以把使用者的健檢紀錄一起刪掉。"""
    repos = github_app.list_repos(row["github_installation_id"])
    if repos:
        supabase.table("repos").upsert(
            [{**r, "user_id": row["user_id"], "installation_id": row["id"]} for r in repos],
            on_conflict="installation_id,github_repo_id",
        ).execute()


def process_installations():
    rows = supabase.table("installations").select("*").eq("status", "pending").limit(20).execute().data
    for row in rows:
        verify_installation(row)


def sync_active_installations():
    """使用者之後到 GitHub 加了 repo，安裝已經存在，不會再走 verify_installation。
    所以每次執行都重拉一次（一個安裝一次 API 呼叫）。"""
    rows = supabase.table("installations").select("*").eq("status", "active").execute().data
    for row in rows:
        try:
            sync_repos(row)
        except github_app.GitHubError:
            log.exception("sync repos for installation %s failed", row["id"])


# ── 2. 跑健檢 ──────────────────────────────────────────────

def _fail(scan_id: str, msg: str):
    supabase.table("scans").update({"status": "failed", "error": msg, "finished_at": _now()}).eq("id", scan_id).execute()


def _over_quota(user_id: str, scan_id: str) -> bool:
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    n = supabase.table("scans").select("id", count="exact").eq("user_id", user_id) \
        .in_("status", ["running", "done"]).gte("created_at", since).neq("id", scan_id).execute().count or 0
    return n >= config.DAILY_SCANS_PER_USER


def process_scan(scan: dict):
    scan_id = scan["id"]
    repo = supabase.table("repos").select("*, installations(*)").eq("id", scan["repo_id"]).single().execute().data
    inst = repo["installations"]
    # 再驗一次：repo、安裝、健檢三者是同一個人，而且安裝已驗證
    if not (repo["user_id"] == scan["user_id"] == inst["user_id"] and inst["status"] == "active"):
        return _fail(scan_id, "這個 repo 不屬於你，或 GitHub App 安裝還沒驗證")
    if _over_quota(scan["user_id"], scan_id):
        return _fail(scan_id, f"今天的健檢次數已用完（每天 {config.DAILY_SCANS_PER_USER} 次），明天再試")

    last = [0.0]

    def on_progress(ev: dict):
        # 進度寫太密會灌爆 Realtime；每秒最多一次，完成那一下一定寫
        if ev["progress"] < 100 and time.monotonic() - last[0] < 1.0:
            return
        last[0] = time.monotonic()
        supabase.table("scans").update({"progress": ev["progress"], "stage": ev["stage"],
                                        "current_file": ev["current_file"], "found": ev["found"]}).eq("id", scan_id).execute()

    workdir = tempfile.mkdtemp(prefix="rd-")
    try:
        on_progress({"progress": 2, "stage": "從 GitHub 下載程式（唯讀）", "current_file": None, "found": 0})
        github_app.shallow_clone(inst["github_installation_id"], repo["full_name"], workdir + "/repo")
        # use_ai 是使用者勾的；伺服器沒開 AI（沒設金鑰）時一律不跑，避免有人直接打 API 硬開
        use_ai = bool(scan["use_ai"] and os.environ.get("ANTHROPIC_API_KEY"))
        report = run_scan(workdir + "/repo", use_ai=use_ai, on_progress=on_progress,
                          project_name=repo["full_name"])
    except github_app.GitHubError as e:
        return _fail(scan_id, str(e))
    except Exception:
        log.exception("scan %s crashed", scan_id)
        return _fail(scan_id, "健檢引擎發生錯誤，我們會查原因")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)   # 掃完立刻刪除程式碼（SPEC 隱私原則）

    rows = [{
        "scan_id": scan_id, "user_id": scan["user_id"], **{k: f[k] for k in (
            "category", "severity", "title", "plain_explanation", "advanced_explanation", "file_path", "line",
            "masked_snippet", "fix_prompt", "fingerprint", "source", "confidence")},
    } for f in report["findings"]]
    for i in range(0, len(rows), 200):
        supabase.table("findings").insert(rows[i:i + 200]).execute()
    supabase.table("scans").update({
        "status": "done", "progress": 100, "stage": "完成", "current_file": None, "found": len(rows),
        "score": report["score"], "category_scores": report["category_scores"], "summary": report["summary"],
        "coverage": report["coverage"], "token_usage": report["token_usage"], "commit_sha": report["commit_sha"],
        "meta": {"project": report["project"], "files_scanned": report["files_scanned"], "languages": report["languages"]},
        "finished_at": _now(),
    }).eq("id", scan_id).execute()
    supabase.table("repos").update({"last_scan_id": scan_id}).eq("id", repo["id"]).execute()


# ── 3. 保存期限與帳號刪除（隱私權政策的承諾，用程式保證） ──

def purge_expired():
    n = supabase.rpc("purge_expired_findings", {"retention_days": config.RETENTION_DAYS}).execute().data
    if n:
        log.info("purged %s expired findings", n)


def process_deletion_requests():
    """使用者按了「刪除我的所有資料」：刪 auth 帳號，profiles 以下全部連帶刪除。"""
    rows = supabase.table("profiles").select("id").not_.is_("delete_requested_at", "null").limit(50).execute().data
    for row in rows:
        try:
            supabase.auth.admin.delete_user(row["id"])
            log.info("deleted account %s", row["id"])
        except Exception:
            log.exception("delete account %s failed; will retry next run", row["id"])


def tick() -> bool:
    """處理一輪。回傳這一輪有沒有做事。"""
    # 這幾件附帶的事失敗（例如 migration 還沒跑、GitHub 抖一下）不可以連累健檢本身
    for job in (process_deletion_requests, purge_expired, sync_active_installations):
        try:
            job()
        except Exception:
            log.exception("%s failed", job.__name__)
    process_installations()
    claimed = supabase.rpc("claim_next_scan").execute().data
    for scan in claimed or []:
        process_scan(scan)
    return bool(claimed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if supabase is None:
        raise SystemExit("沒有設定 SUPABASE_URL / SUPABASE_SECRET_KEY")
    while True:
        busy = tick()
        if args.once and not busy:
            return
        if not busy:
            time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    main()
