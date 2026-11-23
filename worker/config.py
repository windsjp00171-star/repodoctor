"""所有可調的數字都在這裡。模組裡不准寫死模型、價格、匯率、上限。"""

VERSION = "0.1.0"

# ── AI 檢查用哪個模型（2026-11-22 使用者決定：登入權限用 Sonnet，其餘用 Haiku）──
AI_CHECKS = {
    "auth":        {"model": "claude-sonnet-5-5", "effort": "medium", "max_tokens": 16000},
    "duplication": {"model": "claude-haiku-5-5",  "effort": "low",    "max_tokens": 8000},
    "drift":       {"model": "claude-haiku-5-5",  "effort": "low",    "max_tokens": 8000},
}

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
}
# Haiku 5.5 超過 10 萬 token 的請求價格加倍；單次請求上限壓在它下面
HAIKU_LONG_PROMPT_TOKENS = 100_000

USD_TO_TWD = 32.0  # 2026-11-22 使用者決定

# ── 成本上限 ──
MAX_TOKENS_PER_SCAN = 250_000       # 單次健檢所有 AI 呼叫（輸入＋輸出）合計
MAX_INPUT_CHARS_PER_CALL = 150_000  # 單次請求送出的字元數（約 4–5 萬 token）
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
RETENTION_DAYS = 90                 # 健檢細節（findings）保存天數，隱私權政策寫的就是這個數字
