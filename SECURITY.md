# 資安問題回報

RepoDoctor 是幫別人做資安健檢的工具，我們自己的資安更要守好。

## 怎麼回報

**請不要開公開的 issue。** 用 GitHub 的 [Report a vulnerability](../../security/advisories/new) 私下回報，
寫上：問題在哪裡、怎麼重現、可能的影響。我們會盡快回覆，修好之前不會公開細節。

## 範圍

- 網站：https://repodoctor-psi.vercel.app
- 健檢主機（`worker/`）、資料庫權限（`supabase/migrations/`）、GitHub App `repodoctortw`

請不要測試別人的帳號或資料、不要做會影響服務的壓力測試。

## 我們怎麼保護使用者（摘要）

- GitHub App 只有唯讀權限；健檢完立刻刪除程式碼
- 每張資料表都開 RLS，沒登入的人只能透過少數幾個函式拿到有限的資料（有測試守著）
- 送給 AI 之前遮掉所有疑似金鑰，送出前再檢查一次；AI 寫出含危險指令的修復指令會被丟掉
- 健檢主機不執行被健檢的程式碼，也不跟隨 repo 裡的捷徑（symlink）
- 出事時的處理流程：[`docs/INCIDENT.md`](docs/INCIDENT.md)
