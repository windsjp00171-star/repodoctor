# Changelog

## [Unreleased]
### 修正
- 部署時漏設 Supabase 環境變數，網站改成用中文說明少了哪一個，不再只顯示 MIDDLEWARE_INVOCATION_FAILED

### 變更
- 網站從「讀本機資料夾」改成「讀 GitHub repo」；本機版的專案列表與 API 已移除（命令列工具照常可用）
### 新增
- 讓別人也能用（Phase 1，尚未部署）：
  - GitHub 登入（Supabase Auth）＋ GitHub App 唯讀安裝，只讀使用者勾選的 repo
  - 雲端 worker：驗證安裝屬於本人才同步 repo、淺層 clone、掃完立刻刪除程式碼、每人每天健檢次數上限
  - 環境變數改用 Supabase 新的金鑰名稱（publishable key／secret key）
  - 資料表權限全部明寫在 migration（不依賴 Supabase「自動開放新資料表」選項）
  - 資料庫五張表全部開 RLS，使用者只能看自己的資料、只能寫「發起」類欄位；附本機 RLS 測試
  - 掃描進度改用 Supabase Realtime
  - 上線設定說明 `docs/SETUP.md`
- 本機版健檢網站（`web/`，Next.js）：專案列表、一鍵開始健檢、即時掃描進度（目前檔案、已發現問題數）、
  健檢報告（健康分數環、六類別分數、問題卡片、白話／進階切換、一鍵複製修復指令、全部緊急問題合併指令）
- 健檢引擎支援 `--progress-file`，逐筆寫出掃描進度給網站使用
- Phase 0 健檢引擎命令列工具（`worker/`）：輸入本機資料夾，輸出 JSON 健檢報告
- 規則掃描：金鑰外洩、Supabase RLS、專案衛生
- AI 分析：登入與權限、重複與散落、規範落差（只送規則挑出的片段）
- 金鑰遮罩：報告只留前 4 碼；送 Claude API 前全部遮罩，送出前再檢查一次
- 每次健檢記錄 token 用量與估算成本（美金、台幣）
- 專案 CLAUDE.md
