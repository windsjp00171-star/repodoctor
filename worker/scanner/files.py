"""走訪專案資料夾，決定要掃哪些檔案。

有 `.git` 時只看「會被 commit 的檔案」（已追蹤 ＋ 沒被 .gitignore 擋的新檔）——
被 .gitignore 擋住的 `.env` 本來就不會外洩，報出來就是假警報。
Phase 1 是從 GitHub 淺層 clone，本來就只有已 commit 的檔案，行為一致。
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import config


@dataclass
class FileInfo:
    path: str            # 相對路徑，一律用 /
    abspath: Path
    size: int
    tracked: bool | None  # 已被 git 追蹤；None = 沒有 git，無法判斷
    text: str | None = None  # 二進位或太大時為 None

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def ext(self) -> str:
        n = self.name
        return n[n.rfind("."):].lower() if "." in n else ""

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines() if self.text is not None else []


@dataclass
class Project:
    root: Path
    files: list[FileInfo]
    has_git: bool
    commit_sha: str | None = None
    history_env_files: list[str] = field(default_factory=list)  # 歷史裡曾 commit、現在已不在的金鑰類檔名

    def get(self, path: str) -> FileInfo | None:
        return next((f for f in self.files if f.path == path), None)

    def code_files(self) -> list[FileInfo]:
        return [f for f in self.files if f.ext in config.CODE_EXTS and f.text is not None]

    def uses_supabase(self) -> bool:
        """看依賴與 import，不是看有沒有出現 supabase 這個字（文件、註解也會提到它）。"""
        for f in self.files:
            if not f.text:
                continue
            if f.name in ("requirements.txt", "pyproject.toml", "Pipfile") and re.search(r"(?im)^\s*[\"']?supabase\b", f.text):
                return True
            if f.name == "package.json" and "@supabase/" in f.text:
                return True
            if f.ext in config.CODE_EXTS and re.search(r"(?m)^\s*(from\s+supabase\s+import|import\s+supabase\b)|['\"]@supabase/", f.text):
                return True
        return False

    def uses(self, needle: str) -> bool:
        needle = needle.lower()
        return any(f.text and needle in f.text.lower() for f in self.files)


def _git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def _skipped(rel: str) -> bool:
    return any(part in config.SKIP_DIRS for part in rel.split("/")[:-1])


def is_env_like(name: str) -> bool:
    """放金鑰的檔案（.env、私鑰、服務帳號 JSON）。範例檔不算。"""
    n = name.lower()
    if n == ".env" or (n.startswith(".env.") and not n.endswith((".example", ".sample", ".template", ".dist", ".defaults"))):
        return True
    if n.endswith((".pem", ".p12", ".pfx", ".key")) or n in {"id_rsa", "id_ed25519", "id_ecdsa"}:
        return True
    if n.endswith(".json") and (n.startswith(("service-account", "service_account", "client_secret", "serviceaccount"))
                                or n in {"credentials.json", "token.json", "token.pickle"}):
        return True
    return False


def _read_text(p: Path, size: int) -> str | None:
    if size > config.MAX_READ_BYTES:
        return None
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def load_project(root: str | os.PathLike) -> Project:
    root = Path(root).resolve()
    if not root.is_dir():
        raise SystemExit(f"找不到資料夾：{root}")

    has_git = (root / ".git").exists()
    tracked: set[str] = set()
    rels: list[str]
    if has_git and (out := _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")) is not None:
        rels = [r for r in out.split("\0") if r]
        tracked = {r for r in (_git(root, "ls-files", "-z", "--cached") or "").split("\0") if r}
    else:
        has_git = False
        rels = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in config.SKIP_DIRS]
            for fn in filenames:
                rels.append(os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/"))

    files = []
    for rel in sorted(set(rels)):
        if _skipped(rel):
            continue
        p = root / rel
        if not p.is_file() or p.is_symlink():
            continue
        size = p.stat().st_size
        files.append(FileInfo(rel, p, size, (rel in tracked) if has_git else None, _read_text(p, size)))

    proj = Project(root, files, has_git)
    if has_git:
        proj.commit_sha = (_git(root, "rev-parse", "HEAD") or "").strip() or None
        hist = _git(root, "log", "--all", "--diff-filter=A", "--name-only", "--format=")
        current = {f.path for f in files}
        if hist:
            proj.history_env_files = sorted({h for h in hist.splitlines()
                                             if h and is_env_like(h.rsplit("/", 1)[-1]) and h not in current})
    return proj
