# Changelog

## [Unreleased]
### 新增
- Phase 0 健檢引擎命令列工具（`worker/`）：輸入本機資料夾，輸出 JSON 健檢報告
- 規則掃描：金鑰外洩、Supabase RLS、專案衛生
- AI 分析：登入與權限、重複與散落、規範落差（只送規則挑出的片段）
- 金鑰遮罩：報告只留前 4 碼；送 Claude API 前全部遮罩，送出前再檢查一次
- 每次健檢記錄 token 用量與估算成本（美金、台幣）
- 專案 CLAUDE.md
