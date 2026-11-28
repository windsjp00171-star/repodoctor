"""所有可調的數字都在這裡。模組裡不准寫死模型、價格、匯率、上限。"""

VERSION = "0.1.0"

# ── AI 檢查用哪一家、哪個模型 ──
# 2026-11-27 使用者決定：登入與權限要判斷力，用 Anthropic Sonnet；重複與規範落差用 Groq 免費額度。
# 某一家沒有設金鑰時，那一家負責的檢查標成「略過」，不會讓整次健檢失敗。
AI_PROVIDERS = {
    "anthropic": {"env": "ANTHROPIC_API_KEY", "label": "Anthropic Claude"},
    "groq":      {"env": "GROQ_API_KEY",      "label": "Groq",
                  "url": "https://api.groq.com/openai/v1/chat/completions"},
}
AI_CHECKS = {
    "auth":        {"provider": "anthropic", "model": "claude-sonnet-5-5",   "effort": "medium", "max_tokens": 16000},
    # Groq 免費方案每分鐘只有約 8,000 token（2026-11 查 console.groq.com/docs/rate-limits），
    # 所以單次送出壓在 12,000 字元（約 4,000 token），留空間給回答。
    "duplication": {"provider": "groq", "model": "openai/gpt-oss-120b", "effort": "low", "max_tokens": 3000,
                    "max_input_chars": 12_000},
    "drift":       {"provider": "groq", "model": "openai/gpt-oss-120b", "effort": "low", "max_tokens": 3000,
                    "max_input_chars": 12_000},
}
# 免費額度的服務不計費（報告上的成本照實寫 0）；改付費方案時把它從這裡拿掉
FREE_TIER_PROVIDERS = {"groq"}
GROQ_MAX_RETRIES = 3       # 撞到每分鐘上限（HTTP 429）時最多重試幾次
GROQ_MAX_WAIT_SECONDS = 65 # 每次重試最多等多久（每分鐘的額度一分鐘內會恢復）

# Sonnet 5.5 支援伺服器端拒答備援；Haiku 5.5 沒有（官方文件，2026-11）
SERVER_FALLBACK_MODELS = {"claude-sonnet-5-5"}
SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# ── 價格：每百萬 token，美金（Anthropic 官方價，2026-11 查詢；上線前要再確認）──
# cache_write = 5 分鐘快取寫入（輸入價 1.25 倍）；cache_read 依模型倍率不同
PRICES_USD_PER_MTOK = {
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_write": 2.50,  "cache_read": 0.10},
    "claude-haiku-5-5":  {"input": 0.10, "output": 0.50,  "cache_write": 0.125, "cache_read": 0.01},
    "claude-opus-5-5":   {"input": 4.00, "output": 20.00, "cache_write": 5.00,  "cache_read": 0.20},
    "claude-sonnet-5":   {"input": 2.00, "output": 10.00, "cache_write": 2.50,  "cache_read": 0.20},
    # Groq 付費方案的價格（免費方案在 FREE_TIER_PROVIDERS 裡，不計費）；改付費前到 groq.com/pricing 確認
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60, "cache_write": 0.15, "cache_read": 0.15},
}
# Haiku 5.5 超過 10 萬 token 的請求價格加倍；單次請求上限壓在它下面
HAIKU_LONG_PROMPT_TOKENS = 100_000

USD_TO_TWD = 32.0  # 2026-11-22 使用者決定

# ── 成本上限 ──
MAX_TOKENS_PER_SCAN = 250_000       # 單次健檢所有 AI 呼叫（輸入＋輸出）合計
MAX_INPUT_CHARS_PER_CALL = 150_000  # 單次請求送出的字元數（約 4–5 萬 token）


def max_input_chars(check: str) -> int:
    """單次請求最多送多少字元：檢查項目有自己的上限（Groq 免費額度）就用它，否則用全域上限。"""
    return AI_CHECKS[check].get("max_input_chars", MAX_INPUT_CHARS_PER_CALL)
MAX_CALLS_PER_CHECK = 4             # 一個檢查項目最多拆成幾次呼叫
CHARS_PER_TOKEN_ESTIMATE = 3.0      # --dry-run 的粗估（程式碼約 3–4 字元一個 token）

# ── 檔案走訪 ──
SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__", ".next", "dist",
    "build", ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages", ".tox",
    "coverage", ".turbo", ".vercel", ".idea", ".vscode", "staticfiles", "vendor",
}
MAX_READ_BYTES = 2_000_000          # 超過就不讀內容（仍會列入「巨大檔案」）

# ── 專案衛生門檻 ──
LONG_FILE_LINES = 1000              # 程式檔超過這個行數：AI 之後會很難改
HUGE_FILE_BYTES = 5_000_000         # 被 commit 的單一檔案超過這個大小
CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".mjs", ".cjs"}

# ── 雲端 worker（runner.py）──
POLL_SECONDS = 3                    # 沒事做時多久問一次資料庫
DAILY_SCANS_PER_USER = 10           # 測試期每人每天的健檢次數上限（擋濫用與 AI 成本）
GLOBAL_SCANS_PER_DAY = 150          # 全站每天的健檢上限（保護 GitHub Actions 分鐘數；有人開很多帳號狂刷也擋得住）

# ── AI 分析誰能用（還沒串金流，AI 的錢是站長出的）──
# 名單放在環境變數 AI_ALLOWLIST（GitHub 帳號，逗號分隔）。沒設＝沒有人能在網站上用 AI；設成 * ＝所有人。
# 其他人想用 AI：用自己的金鑰在自己電腦跑開源的健檢引擎（python -m cli），金鑰不經過我們。
AI_SCANS_PER_USER_PER_30_DAYS = 20  # 受邀的人也有上限，避免一個人把額度用完
AI_SCANS_GLOBAL_PER_30_DAYS = 100   # 全站 AI 健檢上限：Anthropic 帳戶就算還有錢，也不會一次被用光
RETENTION_DAYS = 90                 # 健檢細節（findings）保存天數，隱私權政策寫的就是這個數字
QUICK_RETENTION_DAYS = 7            # 免登入秒檢的結果保存天數（隱私權政策寫的就是這個數字）
QUICK_MAX_REPO_MB = 200             # 秒檢只接受這麼大以內的 repo（擋有人丟超大 repo 吃掉健檢主機時間）
QUICK_CLONE_TIMEOUT = 120           # 秒檢下載最多等幾秒
