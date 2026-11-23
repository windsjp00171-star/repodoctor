"""金鑰遮罩：只有這一份。

兩個出口，標準刻意不同：
- for_report()：給健檢報告。只處理確定的金鑰，保留前 4 碼。
- Masker.mask()：給 Claude API。確定的 ＋ 高熵字串，一律換成 [已遮罩#N]，一碼都不留。
送出前 `assert_clean()` 會再檢查一次。
"""
from __future__ import annotations

from scanner.files import FileInfo, is_env_like
from scanner.secret_patterns import detect

UNQUOTED_OK_EXTS = {".env", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".properties", ".conf"}


class MaskingError(RuntimeError):
    """送出的文字裡還找得到金鑰。一律中止，不是警告。"""


def allow_unquoted(f: FileInfo) -> bool:
    return is_env_like(f.name) or f.ext in UNQUOTED_OK_EXTS or f.name.lower().startswith(".env")


def preview(value: str) -> str:
    """報告裡唯一能出現的金鑰片段：前 4 碼。"""
    return value[:4] + "…"


def for_report(line: str, allow_unq: bool = False, max_len: int = 200) -> str:
    """把一行程式碼變成可以放進報告的樣子：確定的金鑰留前 4 碼，其他疑似的全遮。"""
    out, pos = [], 0
    for s in detect(line, include_loose=True, allow_unquoted=allow_unq):
        out.append(line[pos:s.start])
        out.append(preview(s.value) if s.confident else "[已遮罩]")
        pos = s.end
    out.append(line[pos:])
    text = "".join(out).strip()
    return text if len(text) <= max_len else text[:max_len] + "…"


class Masker:
    """同一次健檢共用一個：同一把金鑰在不同片段裡會拿到同一個編號。"""

    def __init__(self):
        self._ids: dict[str, int] = {}
        self.known: set[str] = set()   # 整個專案掃到的所有疑似金鑰，assert_clean 用

    def learn(self, f: FileInfo):
        if f.text:
            for s in detect(f.text, include_loose=True, allow_unquoted=allow_unquoted(f)):
                if len(s.value) >= 8:
                    self.known.add(s.value)

    def _tag(self, value: str) -> str:
        n = self._ids.setdefault(value, len(self._ids) + 1)
        return f"[已遮罩#{n}]"

    def mask(self, text: str, allow_unq: bool = False) -> str:
        out, pos = [], 0
        for s in detect(text, include_loose=True, allow_unquoted=allow_unq):
            out.append(text[pos:s.start])
            out.append(self._tag(s.value))
            pos = s.end
        out.append(text[pos:])
        masked = "".join(out)
        # 偵測在片段裡沒認出來、但在完整檔案裡認得出的值（例如變數名被切掉了）
        for v in sorted(self.known, key=len, reverse=True):
            if v in masked:
                masked = masked.replace(v, self._tag(v))
        return masked

    def assert_clean(self, text: str):
        for v in self.known:
            if v in text:
                raise MaskingError(f"送出的內容裡還有疑似金鑰（開頭 {preview(v)}），已中止")
        left = [s for s in detect(text) if s.confident]
        if left:
            raise MaskingError(f"送出的內容裡還有 {left[0].kind}（開頭 {preview(left[0].value)}），已中止")
