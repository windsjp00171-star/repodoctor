# CLAUDE.md — RepoDoctor

給在這個 repo 工作的 Claude Code 看的持久規則。產品規格書（含定價）不在這個公開 repo，存在私人 repo `claude-storage/repodoctor/SPEC.md`，
全域規範（EmmArk）照常適用；本檔只寫這個專案自己的規則。

## 專案是什麼

Vibe coder 的程式健檢醫生：讀一個專案，用中文白話說出哪裡有問題，並產生可以直接貼給
Claude Code 的修復指令。**只讀不寫**——不改使用者的程式、不開 PR。

目前階段：**Phase 1（讓別人也能用）**。網站已部署：https://repodoctor-psi.vercel.app （Vercel）；Supabase 專案 `aikcewsgyetqqjbwdxbo`（東京）；GitHub App `repodoctortw`。上線步驟見 [`docs/SETUP.md`](docs/SETUP.md)。

| 部分 | 在哪裡 | 做什麼 |
|---|---|---|
| 健檢引擎 | `worker/scanner/`、`worker/cli.py` | 給一個資料夾，吐一份報告 |
| 雲端 worker | `worker/runner.py`、`worker/github_app.py` | 從 Supabase 拿待辦 → 驗證 GitHub 安裝 → 唯讀淺層 clone → 健檢 → 寫回 → 刪掉程式碼。目前用 GitHub Actions 免費跑（`.github/workflows/worker.yml`，由 `supabase/migrations/002` 的 trigger 叫醒）；之後可改 Render 常駐，見 SETUP 5B |
| 網站 | `web/`（Next.js） | GitHub 登入、安裝 App、選 repo、Realtime 看進度、報告 |
| 資料庫 | `supabase/migrations/` | SPEC 五張表，全部開 RLS |

### 信任邊界（改這幾個地方要特別小心）
- **授權判斷在 worker，不在網站。** 網站只能寫 `installations.github_installation_id`（一律 pending）與
  `scans.repo_id / use_ai`；「這個 GitHub 安裝是不是這個人的」由 worker 向 GitHub 確認後才標 active。
  網址參數和前端都可以被偽造，worker 是唯一可信的一方。
- 使用者的 GitHub 帳號一律從 `auth.identities` 讀，不讀 `user_metadata`（使用者自己改得到）。
- GitHub token 只放在 git 的 http header，不放進 clone 網址（不會寫進 `.git/config` 或錯誤訊息）。
- 欄位層級權限寫在 migration 裡；`supabase/tests/run.sh` 用一般 Postgres 驗 RLS，改 migration 要跑。

```bash
cd web && npm install && npm run build     # 環境變數見 web/.env.example
cd supabase && PGHOST=/tmp PGPORT=55432 PGUSER=postgres bash tests/run.sh   # RLS 測試（要一個本機 Postgres）
cd worker && python runner.py --once        # 處理完目前的待辦就結束；環境變數見 worker/.env.example
```

```bash
cd worker
pip install -e ".[dev]"
python -m cli <資料夾> -o report.json      # 規則掃描 + AI 分析
python -m cli <資料夾> --no-ai             # 只跑規則掃描，不花錢
python -m cli <資料夾> --dry-run           # 列出會送什麼給 AI（已遮罩）與預估 token，不呼叫 API
pytest
```

## 規則（SPEC「專案 CLAUDE.md 規則」）

適用範圍標在後面。標「Phase 1」的現在還沒有對應的程式碼，寫進來是為了之後不用再找。

- **worker：只在 `worker/db.py` 建立 Supabase client，其他地方一律 `from db import supabase`**（現在適用）
- **service role key 只能出現在 worker，絕不能出現在前端任何檔案**（現在適用：worker 以外不准出現）
- 前端只在 `lib/supabase/client.ts` 與 `lib/supabase/server.ts` 建立 Supabase client（Phase 1）
- 登入保護只在 `middleware.ts` 統一處理，頁面裡不各自寫登入檢查（Phase 1）
- 顏色、圓角、間距只用設計 token，元件裡不出現寫死的色碼（Phase 1）
- 動畫參數集中在 `lib/motion.ts`（Phase 1）
- 所有介面文字使用繁體中文，集中放在文案檔（Phase 1；worker 的報告文字也是繁中）

★ 這份 CLAUDE.md 本身也是健檢「規範落差」的第一個測試對象。改規則時記得程式要跟上。

## Phase 0 自己的規則

### 金鑰
- **金鑰完整值不可以寫進報告、log、測試輸出，也不可以送給 Claude API。**
  報告只留「前 4 碼 + 檔案 + 行號」。
- 遮罩只有一份實作：`scanner/masking.py`。不要在別的地方自己寫一份。
- 報告和送 API 用**兩套標準**，刻意不同：
  - 報告只報「確定是金鑰」的（已知格式、或變數名像金鑰而且值像金鑰）—— 假警報少，報告才可信
  - 送 API 前多遮一層：再加上高熵長字串，一律換成 `[已遮罩#N]`，連前 4 碼都不留 —— 寧可多遮
- `.env` 這類檔案的內容**完全不送** API。
- 送出前 `ai/client.py` 會再掃一次：送出的文字裡還找得到原本的金鑰就**中止**，不是警告。

### 呼叫 Claude API
- 只有 `scanner/ai/client.py` 可以呼叫 API。其他模組把片段交給它。
- 只送規則掃描挑出的片段，**不送整個 repo**。
- 模型、effort、價格、匯率、單次 token 上限都在 `config.py`，模組裡不准寫死。
- 每次呼叫都要把 `usage` 記進報告的 `token_usage`（依檢查項目、模型分開），並換算美金與台幣。
- 超過單次 token 上限就中止剩下的 AI 檢查，在報告裡寫明，**不可以默默跳過**。
- AI 檢查失敗（網路、拒答、格式錯）要在報告裡記成「這一項沒有檢查完」，
  **不可以當成「沒有發現問題」** —— 那兩件事對使用者的意思相反。

### 報告
- 欄位對齊 SPEC 的 `scans` / `findings` 表，Phase 1 可以直接寫進資料庫。
- 規則類問題的白話說明與修復指令用**固定中文模板**（`scanner/rules/` 裡），不花 AI 的錢。
- `fingerprint` 不可以包含行號（改一行無關的程式，同一個問題的 fingerprint 不能變）。

### 測試
- 守衛測試要「把它守的東西改壞一次會紅」才算數。
- 掃原始碼的斷言先去掉註解與 docstring，不然會被自己的說明文字騙過。
- 測試用的假金鑰要組字串產生（`"sk-ant-" + "x" * 40`），不要整串寫在原始碼裡 —— 不然本工具掃自己會報警，GitHub 也會報警。

## 開發流程

- **這是公開 repo（AGPL-3.0）**：不要 commit 金鑰、使用者資料、商業計畫或真實的健檢報告；示範一律用假資料
- 每次 commit 前更新 `CHANGELOG.md`（Rule 16）
- 工作階段結束輸出 Session Snapshot（Rule 13）
- 測試通過就直接合併，不用再問（Rule 19）
