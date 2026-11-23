"""送給 AI 的內容：金鑰一碼都不能出現；AI 失敗不能被讀成「沒有問題」；成本要記下來。"""
import pytest

from cli import scan
from scanner.ai.client import AICheckError, AIClient, cost_usd
from scanner.ai.common import to_findings
from scanner.masking import Masker
from tests.conftest import FAKE


def test_dry_run_payloads_contain_no_secrets(leaky_flask):
    r = scan(str(leaky_flask), use_ai=True, dry_run=True)
    assert r["dry_run_payloads"], "dry-run 應該列出會送出的內容"
    sent = "\n".join(p["system"] + p["user"] for p in r["dry_run_payloads"])
    for name, v in FAKE.items():
        assert v not in sent, name
        assert v[:8] not in sent, name     # 送 AI 的連前幾碼都不留
    assert "[已遮罩#" in sent
    assert r["token_usage"]["estimated"] is True and r["token_usage"]["total"]["cost_usd"] > 0


def test_env_files_are_never_sent(leaky_flask):
    r = scan(str(leaky_flask), use_ai=True, dry_run=True)
    assert all(".env" not in p["user"].split("（")[0] for p in r["dry_run_payloads"])
    assert not any("### .env" in p["user"] for p in r["dry_run_payloads"])


def test_assert_clean_blocks_leak_even_if_mask_was_skipped():
    m = Masker()
    m.known.add(FAKE["dropbox"])
    ai = AIClient(m, dry_run=True)
    with pytest.raises(AICheckError):
        ai.ask("auth", "sys", "x = '" + FAKE["dropbox"] + "'", {})   # 呼叫端忘了 mask
    with pytest.raises(AICheckError):
        ai.ask("auth", "sys", 'k = "' + FAKE["anthropic"] + '"', {})  # 連 known 都沒登記也要擋
    assert ai.payloads == []


def test_budget_stops_further_calls(monkeypatch):
    import config
    monkeypatch.setattr(config, "MAX_TOKENS_PER_SCAN", 10)
    ai = AIClient(Masker(), dry_run=True)
    with pytest.raises(AICheckError):
        ai.ask("auth", "sys", "x" * 300, {})


def test_failed_ai_check_is_not_a_clean_bill(leaky_flask, monkeypatch):
    def boom(self, *a, **k):
        raise AICheckError("連不上 Claude API")
    monkeypatch.setattr(AIClient, "ask", boom)
    r = scan(str(leaky_flask), use_ai=True)
    assert r["coverage"]["auth"]["status"] == "failed"
    assert r["category_scores"]["auth"] is None          # 不可以給 100 分
    assert "連不上" in r["coverage"]["auth"]["note"]


def test_ai_answers_citing_unsent_files_or_low_confidence_are_dropped():
    item = dict(title="t", subject="s", severity="high", confidence="high", file_path="routes/a.py", line=3,
                plain_explanation="p", advanced_explanation="a", fix_prompt="f")
    data = {"findings": [item, {**item, "file_path": "made_up.py"}, {**item, "confidence": "low"}], "notes": ""}
    fs, dropped = to_findings(data, "auth", "ai.auth", {"routes/a.py"})
    assert [f.file_path for f in fs] == ["routes/a.py"]
    assert dropped == {"low_confidence": 1, "unknown_file": 1}


def test_cost_math():
    u = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert cost_usd("claude-sonnet-5-5", u) == pytest.approx(12.0)
    assert cost_usd("claude-haiku-5-5", u) == pytest.approx(0.60)


def test_check_ai_without_key_explains_in_chinese(monkeypatch, capsys):
    from cli import main
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["--check-ai"]) == 1
    assert "沒有設定 ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_check_ai_with_bad_key_does_not_echo_key(monkeypatch, capsys):
    import anthropic
    from cli import main
    fake = "sk-" + "ant-" + "Zz9" * 14
    monkeypatch.setenv("ANTHROPIC_API_KEY", fake)

    class Boom:
        def __init__(self, *a, **k):
            self.messages = self

        def create(self, **k):
            import httpx2 as httpx
            req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            raise anthropic.AuthenticationError("bad", response=httpx.Response(401, request=req), body=None)
    monkeypatch.setattr(anthropic, "Anthropic", Boom)
    assert main(["--check-ai"]) == 1
    err = capsys.readouterr().err
    assert "金鑰無效" in err and fake not in err
