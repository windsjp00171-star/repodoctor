"""唯一呼叫 Claude API 的地方。

每次呼叫：送出前檢查遮罩 → 檢查預算 → 呼叫 → 記 usage 與成本。
任何失敗都丟 AICheckError，呼叫端要記成「這一項沒有檢查完」，不可以當成「沒有問題」。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import config
from scanner.masking import Masker, MaskingError


class AICheckError(RuntimeError):
    pass


class BudgetExceeded(AICheckError):
    pass


def cost_usd(model: str, u: dict) -> float:
    p = config.PRICES_USD_PER_MTOK.get(model) or config.PRICES_USD_PER_MTOK[config.AI_CHECKS["auth"]["model"]]
    return (u.get("input_tokens", 0) * p["input"]
            + u.get("output_tokens", 0) * p["output"]
            + u.get("cache_creation_input_tokens", 0) * p["cache_write"]
            + u.get("cache_read_input_tokens", 0) * p["cache_read"]) / 1_000_000


@dataclass
class Usage:
    calls: list[dict] = field(default_factory=list)
    estimated: bool = False   # --dry-run 時是粗估，不是 API 回報的數字

    @property
    def total_tokens(self) -> int:
        return sum(c["input_tokens"] + c["output_tokens"] + c.get("cache_creation_input_tokens", 0)
                   + c.get("cache_read_input_tokens", 0) for c in self.calls)

    def to_dict(self) -> dict:
        keys = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]
        total = {k: sum(c.get(k, 0) for c in self.calls) for k in keys}
        usd = sum(c["cost_usd"] for c in self.calls)
        by_check: dict[str, dict] = {}
        for c in self.calls:
            b = by_check.setdefault(c["check"], {"calls": 0, "tokens": 0, "cost_usd": 0.0})
            b["calls"] += 1
            b["tokens"] += c["input_tokens"] + c["output_tokens"]
            b["cost_usd"] = round(b["cost_usd"] + c["cost_usd"], 6)
        return {
            "estimated": self.estimated,
            "calls": self.calls,
            "by_check": by_check,
            "total": {**total, "cost_usd": round(usd, 6), "cost_twd": round(usd * config.USD_TO_TWD, 2)},
            "usd_to_twd": config.USD_TO_TWD,
            "max_tokens_per_scan": config.MAX_TOKENS_PER_SCAN,
        }


class AIClient:
    def __init__(self, masker: Masker, dry_run: bool = False):
        self.masker = masker
        self.dry_run = dry_run
        self.usage = Usage(estimated=dry_run)
        self.payloads: list[dict] = []   # --dry-run 時給使用者看「會送出什麼」
        self._client = None

    def _sdk(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(max_retries=3)
        return self._client

    def ask(self, check: str, system: str, user: str, schema: dict) -> dict:
        """送一次請求，回傳符合 schema 的 dict。user 必須已經過 masker.mask()。"""
        cfg = config.AI_CHECKS[check]
        try:
            self.masker.assert_clean(system + "\n" + user)
        except MaskingError as e:
            raise AICheckError(str(e)) from e
        if len(user) > config.MAX_INPUT_CHARS_PER_CALL:
            raise AICheckError(f"單次送出 {len(user):,} 字元，超過上限 {config.MAX_INPUT_CHARS_PER_CALL:,}")

        est_in = int((len(system) + len(user)) / config.CHARS_PER_TOKEN_ESTIMATE)
        if self.usage.total_tokens + est_in > config.MAX_TOKENS_PER_SCAN:
            raise BudgetExceeded(f"預估會超過單次健檢上限 {config.MAX_TOKENS_PER_SCAN:,} token，已停止")

        if self.dry_run:
            est_out = 1500
            u = {"input_tokens": est_in, "output_tokens": est_out}
            self.usage.calls.append({"check": check, "model": cfg["model"], **u,
                                     "cost_usd": round(cost_usd(cfg["model"], u), 6)})
            self.payloads.append({"check": check, "model": cfg["model"], "chars": len(user),
                                  "est_input_tokens": est_in, "system": system, "user": user})
            return {"findings": [], "notes": "（dry-run：沒有呼叫 API）"}

        import anthropic
        kwargs = dict(
            model=cfg["model"], max_tokens=cfg["max_tokens"], system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": cfg["effort"], "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            if cfg["model"] in config.SERVER_FALLBACK_MODELS:
                resp = self._sdk().beta.messages.create(
                    **kwargs, betas=[config.SERVER_FALLBACK_BETA], fallbacks="default")
            else:
                resp = self._sdk().messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise AICheckError("Claude API 金鑰無效或沒有設定（ANTHROPIC_API_KEY）") from e
        except anthropic.RateLimitError as e:
            raise AICheckError("Claude API 流量限制，請稍後再試") from e
        except anthropic.APIStatusError as e:
            raise AICheckError(f"Claude API 錯誤（HTTP {e.status_code}）") from e
        except anthropic.APIConnectionError as e:
            raise AICheckError("連不上 Claude API") from e

        u = resp.usage
        ud = {"input_tokens": u.input_tokens or 0, "output_tokens": u.output_tokens or 0,
              "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
              "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0}
        served = resp.model or cfg["model"]
        self.usage.calls.append({"check": check, "model": served, **ud,
                                 "cost_usd": round(cost_usd(served, ud), 6),
                                 "stop_reason": resp.stop_reason, "request_id": getattr(resp, "_request_id", None)})

        if resp.stop_reason == "refusal":
            raise AICheckError("模型拒絕回答這一段")
        if resp.stop_reason == "max_tokens":
            raise AICheckError("回答被截斷（超過 max_tokens）")
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), None)
        if not text:
            raise AICheckError("模型沒有回傳內容")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise AICheckError("模型回傳的格式不正確") from e
