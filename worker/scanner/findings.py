"""單一問題的資料結構。欄位對齊 SPEC 的 findings 表，Phase 1 可以直接寫進資料庫。"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

CATEGORIES = {
    "secrets": "金鑰外洩",
    "database": "資料庫權限",
    "auth": "登入與權限",
    "duplication": "重複與散落",
    "drift": "規範落差",
    "hygiene": "專案衛生",
}
SEVERITIES = {"critical": "緊急", "high": "高", "medium": "中", "low": "低"}
SEVERITY_ORDER = ["critical", "high", "medium", "low"]


@dataclass
class Finding:
    category: str
    severity: str
    title: str
    plain_explanation: str
    advanced_explanation: str
    fix_prompt: str
    rule_id: str                     # 例如 secrets.known_format、ai.auth
    file_path: str | None = None
    line: int | None = None
    masked_snippet: str | None = None
    source: str = "rule"             # rule / ai
    confidence: str | None = None    # AI 類才有
    fingerprint_key: str = ""        # 組 fingerprint 的材料；不含行號
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        assert self.category in CATEGORIES, self.category
        assert self.severity in SEVERITIES, self.severity

    @property
    def fingerprint(self) -> str:
        # 不含行號：改一行無關的程式，同一個問題的 fingerprint 不能變
        raw = "|".join([self.rule_id, self.file_path or "", self.fingerprint_key or self.title])
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("fingerprint_key")
        d["fingerprint"] = self.fingerprint
        d["category_label"] = CATEGORIES[self.category]
        d["severity_label"] = SEVERITIES[self.severity]
        return d
