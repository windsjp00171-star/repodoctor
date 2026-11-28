"""GitHub App：唯一跟 GitHub 講話的地方。權限只有 Contents: read、Metadata: read。

- app_jwt()：用 App 私鑰簽的短期 JWT（10 分鐘），只用來換安裝 token、查安裝資訊
- installation_token()：某個安裝的短期 token（1 小時），用來 clone 和列 repo
- shallow_clone()：淺層 clone 到暫存資料夾。token 只放在 git 的 http header，不寫進網址，
  所以不會出現在 .git/config、錯誤訊息或 log 裡。
"""
from __future__ import annotations

import base64
import os
import subprocess
import time

import requests

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


def _private_key() -> str:
    key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
    if not key and os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH"):
        with open(os.environ["GITHUB_APP_PRIVATE_KEY_PATH"], encoding="utf-8") as fp:
            key = fp.read()
    if not key:
        raise GitHubError("沒有設定 GITHUB_APP_PRIVATE_KEY")
    return key.replace("\\n", "\n")


def app_jwt() -> str:
    import jwt  # PyJWT

    app_id = os.environ.get("GITHUB_APP_ID")
    if not app_id:
        raise GitHubError("沒有設定 GITHUB_APP_ID")
    now = int(time.time())
    return jwt.encode({"iat": now - 60, "exp": now + 540, "iss": app_id}, _private_key(), algorithm="RS256")


def _req(method: str, path: str, token: str, *, bearer_app: bool = False, **kw) -> dict | list:
    r = requests.request(method, API + path, timeout=30, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repodoctor-worker",
    }, **kw)
    if r.status_code >= 400:
        raise GitHubError(f"GitHub API {method} {path} 回 HTTP {r.status_code}")
    return r.json()


def get_installation(installation_id: int) -> dict:
    """回 {account_login, account_type}。"""
    data = _req("GET", f"/app/installations/{installation_id}", app_jwt())
    acct = data.get("account") or {}
    return {"account_login": acct.get("login"), "account_type": acct.get("type")}


def installation_token(installation_id: int) -> str:
    data = _req("POST", f"/app/installations/{installation_id}/access_tokens", app_jwt())
    return data["token"]


def list_repos(installation_id: int) -> list[dict]:
    token = installation_token(installation_id)
    repos, page = [], 1
    while True:
        data = _req("GET", f"/installation/repositories?per_page=100&page={page}", token)
        batch = data.get("repositories", [])
        repos += [{"github_repo_id": r["id"], "full_name": r["full_name"], "default_branch": r.get("default_branch"),
                   "language": r.get("language")} for r in batch]
        if len(batch) < 100 or page >= 20:
            return repos
        page += 1


def shallow_clone(installation_id: int, full_name: str, dest: str):
    token = installation_token(installation_id)
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    cmd = ["git", "-c", f"http.extraHeader=Authorization: Basic {basic}", "clone", "--depth", "1", "--quiet",
           "--no-tags", f"https://github.com/{full_name}.git", dest]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"})
    if r.returncode != 0:
        # stderr 可能含網址，但不含 token（token 只在 header 裡）
        raise GitHubError(f"clone 失敗：{r.stderr.strip()[-300:]}")


def public_shallow_clone(full_name: str, dest: str, timeout: int = 120):
    """免登入秒檢用：不帶任何權限下載公開 repo。私人 repo 會因為要求登入而失敗——這正是我們要的。"""
    cmd = ["git", "-c", "credential.helper=", "clone", "--depth", "1", "--quiet", "--no-tags",
           f"https://github.com/{full_name}.git", dest]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1",
                                "GIT_ASKPASS": "true"})
    except subprocess.TimeoutExpired as e:
        raise GitHubError("這個 repo 太大，下載超過時間；請登入後用 GitHub App 健檢") from e
    if r.returncode != 0:
        raise GitHubError("找不到這個公開 repo（網址打錯，或它是私人 repo——私人 repo 請登入後健檢）")
