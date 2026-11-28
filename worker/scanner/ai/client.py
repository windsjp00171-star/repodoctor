"""唯一呼叫 AI API 的地方（Anthropic Claude、Groq）。

每次呼叫：送出前檢查遮罩 → 檢查預算 → 依 config.AI_CHECKS 的 provider 呼叫 → 記 usage 與成本。
遮罩檢查與預算在分流之前，所以不管送哪一家，同一套保護都跑過。
任何失敗都丟 AICheckError，呼叫端要記成「這一項沒有檢查完」，不可以當成「沒有問題」。
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

import config
from scanner.masking import Masker, MaskingError


class AICheckError(RuntimeError):
    pass


class BudgetExceeded(AICheckError):
    pass


def provider_of(check: str) -> str:
    return config.AI_CHECKS[check].get("provider", "anthropic")


def has_key(check: str) -> bool:
    """這個檢查項目要用的那一家，有沒有設金鑰。"""
    return bool(os.environ.get(config.AI_PROVIDERS[provider_of(check)]["env"]))


def missing_key_note(check: str) -> str:
    prov = config.AI_PROVIDERS[provider_of(check)]
    return f"沒有設定 {prov['env']}（{prov['label']}），這一項沒有檢查"


def cost_usd(model: str, u: dict, provider: str = "anthropic") -> float:
    if provider in config.FREE_TIER_PROVIDERS:
        return 0.0
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
        limit = config.max_input_chars(check)
        if len(user) > limit:
            raise AICheckError(f"單次送出 {len(user):,} 字元，超過上限 {limit:,}")

        est_in = int((len(system) + len(user)) / config.CHARS_PER_TOKEN_ESTIMATE)
        if self.usage.total_tokens + est_in > config.MAX_TOKENS_PER_SCAN:
            raise BudgetExceeded(f"預估會超過單次健檢上限 {config.MAX_TOKENS_PER_SCAN:,} token，已停止")

        if self.dry_run:
            est_out = 1500
            u = {"input_tokens": est_in, "output_tokens": est_out}
            prov = provider_of(check)
            self.usage.calls.append({"check": check, "provider": prov, "model": cfg["model"], **u,
                                     "cost_usd": round(cost_usd(cfg["model"], u, prov), 6)})
            self.payloads.append({"check": check, "provider": prov, "model": cfg["model"], "chars": len(user),
                                  "est_input_tokens": est_in, "system": system, "user": user})
            return {"findings": [], "notes": "（dry-run：沒有呼叫 API）"}

        if provider_of(check) == "groq":
            return self._ask_groq(check, cfg, system, user, schema)
        return self._ask_anthropic(check, cfg, system, user, schema)

    def _ask_anthropic(self, check: str, cfg: dict, system: str, user: str, schema: dict) -> dict:
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
        self.usage.calls.append({"check": check, "provider": "anthropic", "model": served, **ud,
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

    def _ask_groq(self, check: str, cfg: dict, system: str, user: str, schema: dict) -> dict:
        """Groq（OpenAI 相容格式）。免費方案每分鐘額度很小：撞到 429 就照 retry-after 等一下再試。"""
        body = {
            "model": cfg["model"],
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_completion_tokens": cfg["max_tokens"],
            "reasoning_effort": cfg["effort"],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": f"repodoctor_{check}", "strict": True, "schema": schema}},
        }
        resp = _groq_post(body)
        data = resp.json()
        u = data.get("usage") or {}
        ud = {"input_tokens": u.get("prompt_tokens", 0) or 0, "output_tokens": u.get("completion_tokens", 0) or 0}
        served = data.get("model") or cfg["model"]
        choice = (data.get("choices") or [{}])[0]
        self.usage.calls.append({"check": check, "provider": "groq", "model": served, **ud,
                                 "cost_usd": round(cost_usd(served, ud, "groq"), 6),
                                 "stop_reason": choice.get("finish_reason"), "request_id": data.get("id")})
        if choice.get("finish_reason") == "length":
            raise AICheckError("回答被截斷（超過 max_tokens）")
        text = (choice.get("message") or {}).get("content")
        if not text:
            raise AICheckError("模型沒有回傳內容")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise AICheckError("模型回傳的格式不正確") from e


def _groq_post(body: dict):
    """送到 Groq。錯誤一律轉成中文的 AICheckError；回應內容和金鑰都不放進錯誤訊息。"""
    import requests

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise AICheckError("沒有設定 GROQ_API_KEY")
    url = config.AI_PROVIDERS["groq"]["url"]
    for attempt in range(config.GROQ_MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=body, timeout=120,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        except requests.RequestException as e:
            raise AICheckError("連不上 Groq API") from e
        if resp.status_code == 429 and attempt < config.GROQ_MAX_RETRIES:
            try:
                wait = float(resp.headers.get("retry-after") or 20)
            except ValueError:
                wait = 20.0
            time.sleep(min(max(wait, 1.0), config.GROQ_MAX_WAIT_SECONDS))
            continue
        if resp.status_code == 401:
            raise AICheckError("Groq API 金鑰無效（GROQ_API_KEY）")
        if resp.status_code == 429:
            raise AICheckError("Groq 免費額度用完（每分鐘或每天的上限），請稍後再試")
        if resp.status_code >= 400:
            raise AICheckError(f"Groq API 錯誤（HTTP {resp.status_code}）")
        return resp
    raise AICheckError("Groq 免費額度用完，請稍後再試")


def check_key() -> str:
    """用最便宜的模型打一次極短的請求，確認金鑰可用。不送任何程式碼。

    給「明天放好金鑰後先測一下」用：成功回一段中文說明，失敗丟 AICheckError（中文原因）。
    """
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_groq = bool(os.environ.get("GROQ_API_KEY"))
    if not has_anthropic and not has_groq:
        raise AICheckError("沒有設定 ANTHROPIC_API_KEY 也沒有設定 GROQ_API_KEY（GitHub Actions 的 secret 名稱要一字不差）")
    # 兩家各測各的：一家失敗不可以讓另一家沒測到
    lines, failed = [], False
    for name, has, fn in (("Anthropic", has_anthropic, _check_anthropic), ("Groq", has_groq, _check_groq)):
        if not has:
            continue
        try:
            lines.append(fn())
        except AICheckError as e:
            failed = True
            lines.append(f"{name} 金鑰測試失敗：{e}")
    if failed:
        raise AICheckError("\n".join(lines))
    return "\n".join(lines)


def _model_of(provider: str) -> str:
    """測金鑰要用那一家真的會用到的模型（不可以拿別家的模型名稱去問）。"""
    return next(c["model"] for c in config.AI_CHECKS.values() if c.get("provider", "anthropic") == provider)


def _check_groq() -> str:
    model = _model_of("groq")
    resp = _groq_post({"model": model, "max_completion_tokens": 64, "reasoning_effort": "low",
                       "messages": [{"role": "user", "content": "請只回覆：OK"}]})
    u = resp.json().get("usage") or {}
    return f"Groq 金鑰可以用。模型 {model}，這次測試用了 {u.get('total_tokens', 0)} 個 token（免費額度）"


def _check_anthropic() -> str:
    import anthropic

    model = _model_of("anthropic")
    try:
        resp = anthropic.Anthropic(max_retries=1).messages.create(
            model=model, max_tokens=64, output_config={"effort": "low"},
            messages=[{"role": "user", "content": "請只回覆：OK"}],
        )
    except anthropic.AuthenticationError as e:
        raise AICheckError("金鑰無效：請確認貼上的是完整的金鑰（sk-ant- 開頭），而且沒有多餘的空白") from e
    except anthropic.PermissionDeniedError as e:
        raise AICheckError("金鑰沒有權限：請到 Anthropic Console 確認這把金鑰所在的 workspace 可以用 API") from e
    except anthropic.RateLimitError as e:
        raise AICheckError("額度或流量不足：請到 Anthropic Console 確認已儲值、或花費上限還沒用完") from e
    except anthropic.APIStatusError as e:
        raise AICheckError(f"Claude API 回 HTTP {e.status_code}") from e
    except anthropic.APIConnectionError as e:
        raise AICheckError("連不上 Claude API") from e
    u = resp.usage
    ud = {"input_tokens": u.input_tokens or 0, "output_tokens": u.output_tokens or 0}
    usd = cost_usd(resp.model or model, ud)
    return (f"Anthropic 金鑰可以用。模型 {resp.model}，這次測試用了 {ud['input_tokens'] + ud['output_tokens']} 個 token，"
            f"約 US${usd:.6f}（NT${usd * config.USD_TO_TWD:.4f}）")
