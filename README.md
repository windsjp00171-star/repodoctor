# RepoDoctor

Vibe coder 的程式健檢醫生：連上 GitHub，用中文白話告訴你專案哪裡有問題，並產生可以直接貼給 Claude Code 的修復指令。

**網站：https://repodoctor-psi.vercel.app**

## 它檢查什麼

| 類別 | 怎麼檢查 |
|---|---|
| 金鑰外洩 | 規則掃描（已知格式、變數名＋值的熵） |
| Supabase 資料表權限（RLS） | 規則掃描 migration |
| 專案衛生（`.env` 被 commit、超長檔案、重複的 Supabase client…） | 規則掃描 |
| 登入與權限、重複程式、規範落差（程式跟 CLAUDE.md 對不上） | AI 分析（選用） |

## 隱私設計

- GitHub App 只有**唯讀**權限（Contents、Metadata），改不了你的程式
- 程式碼只在健檢時暫時下載，健檢結束立刻刪除；資料庫裡沒有程式碼
- 報告裡的金鑰只留前 4 碼；送給 AI 之前全部遮罩，送出前再檢查一次，漏網就中止
- 「這個 GitHub 安裝是不是你的」由 worker 向 GitHub 確認，網站和網址參數都不被信任
- 每張資料表都開 RLS，每個人只讀得到自己的資料（`supabase/tests/` 有測試）
- 問題細節保存 90 天；可以一鍵刪除帳號與全部資料

詳細說明見網站的〈隱私與安全〉頁，以及 [`CLAUDE.md`](CLAUDE.md) 的信任邊界。

## 架構

| 部分 | 在哪裡 | 技術 |
|---|---|---|
| 健檢引擎 | `worker/scanner/`、`worker/cli.py` | Python、Claude API |
| 雲端 worker | `worker/runner.py` | GitHub Actions（由 Supabase 叫醒） |
| 網站 | `web/` | Next.js、Tailwind |
| 資料庫 | `supabase/migrations/` | Supabase Postgres、RLS、Realtime |

## 本機使用健檢引擎

```bash
cd worker
pip install -e ".[dev]"
python -m cli <資料夾> --no-ai      # 只跑規則掃描，不花錢
python -m cli <資料夾> --dry-run    # 看會送什麼給 AI（已遮罩）、預估 token，不呼叫 API
pytest
```

自己架一套的步驟見 [`docs/SETUP.md`](docs/SETUP.md)；出事時的處理見 [`docs/INCIDENT.md`](docs/INCIDENT.md)。

## 回報資安問題

請不要開公開的 issue。用 GitHub 的 [Report a vulnerability](../../security/advisories/new) 私下回報。

## 授權

[GNU AGPL-3.0](LICENSE)。你可以自由使用、修改；但如果把修改後的版本架成網站提供別人使用，也必須公開你的原始碼。

---

作者 EMMARK 的其他作品與履歷：[作品集](https://windsjp00171-star.github.io/CLAUDE-DESIGN/)
