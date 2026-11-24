# RepoDoctor 上線設定

這份是「讓別人也能用」要做的設定。程式都寫好了，下面這些要用你的帳號操作，Claude 沒辦法代做。
照順序做，大約 40 分鐘。每一步做完會拿到一些值，記在手邊，最後一步填進部署平台。

> 有 ★ 的是會花錢的地方。

---

## 1. Supabase（資料庫＋登入）

1. 到 https://supabase.com 建一個新專案（Free 方案就夠測試期用）：
   - Project name：`repodoctor`
   - Database password：按 Generate，存進密碼管理器（網站和 worker 用不到，你自己進資料庫才用）
   - Region：**Northeast Asia (Tokyo)**（不要用 Auto）
   - GitHub (optional)：不用連
   - Enable Data API：**勾**
   - Grant API access to new tables automatically：**不要勾**（權限已經寫在 migration 裡，不靠自動開放）
2. 左邊 **SQL Editor** → 貼上 `supabase/migrations/001_init.sql` 的全部內容 → Run。
3. 左邊 **Project Settings → API Keys**，記下：
   - **Publishable key**（`sb_publishable_` 開頭）→ `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`（這把可以公開）
   - **Secret key**（`sb_secret_` 開頭，在同一頁下面的 Secret keys）→ `SUPABASE_SECRET_KEY`（**這把絕對不能外流，只給 worker**）
   - **Project URL**（專案首頁上的 `https://xxxx.supabase.co`）→ `NEXT_PUBLIC_SUPABASE_URL` 和 `SUPABASE_URL`

## 2. GitHub 登入用的 OAuth App

這是「用 GitHub 登入網站」用的，跟下一步的 GitHub App 是兩個東西（SPEC：登入與安裝分開）。

1. GitHub → Settings → Developer settings → **OAuth Apps** → New OAuth App
   - Application name：`RepoDoctor`
   - Homepage URL：你的網站網址（還沒有就先填 `https://example.com`，部署後再改）
   - Authorization callback URL：`https://<你的 Supabase 專案>.supabase.co/auth/v1/callback`
2. 建好後按 **Generate a new client secret**，記下 Client ID 和 Client secret。
3. 回到 Supabase → **Authentication → Sign In / Providers → GitHub** → 打開，貼上 Client ID 和 secret → Save。
4. Supabase → **Authentication → URL Configuration**
   - Site URL：你的網站網址
   - Redirect URLs：加一行 `https://你的網站網址/auth/callback`

## 3. GitHub App（讀使用者的 repo）

1. GitHub → Settings → Developer settings → **GitHub Apps** → New GitHub App
   - GitHub App name：`RepoDoctor`（名字要全 GitHub 唯一，被用走就加字）
   - Homepage URL：你的網站網址
   - **Setup URL**：`https://你的網站網址/github/setup`，並勾 **Redirect on update**
   - **Webhook**：把 Active 取消勾選（我們不用 webhook）
   - **Repository permissions**：只開兩個
     - Contents：**Read-only**
     - Metadata：Read-only（預設就有）
   - 其他權限全部不開
   - Where can this GitHub App be installed：**Any account**
2. 建好後記下：
   - **App ID**（頁面上方）→ `GITHUB_APP_ID`
   - 網址最後那段（`github.com/apps/這一段`）→ `NEXT_PUBLIC_GITHUB_APP_SLUG`
3. 頁面最下面 **Generate a private key** → 會下載一個 `.pem` 檔 → 內容就是 `GITHUB_APP_PRIVATE_KEY`
   （**這個檔案不要放進任何 repo**）

## 4. 部署網站（Vercel）

1. https://vercel.com → Add New Project → 選 `repodoctor` 這個 repo
2. **Root Directory** 選 `web`
3. Environment Variables：

   | 名稱 | 值 |
   |---|---|
   | `NEXT_PUBLIC_SUPABASE_URL` | 步驟 1 |
   | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | 步驟 1 的 publishable key |
   | `NEXT_PUBLIC_GITHUB_APP_SLUG` | 步驟 3 |
   | `NEXT_PUBLIC_AI_ENABLED` | 先填 `false`；worker 設好 Anthropic 金鑰後改 `true` |

   **不要**把 secret key、GitHub 私鑰填在這裡。
4. Deploy。拿到網址後，回去把步驟 2、3 裡的「你的網站網址」改成真的網址。

★ Vercel 免費方案只限非商業用途，開始收費時要升級（SPEC 有寫）。

## 5. 健檢主機（worker）

健檢主機負責：確認 GitHub 安裝是本人的、下載 repo、跑健檢、寫回結果。有兩種跑法，**程式一樣**：

| | 5A. GitHub Actions（**目前用這個**） | 5B. Render（之後要正式給別人用再開） |
|---|---|---|
| 費用 | 0（私人 repo 每月 2,000 分鐘免費額度內） | ★ 約 US$7／月（Background Worker 沒有免費方案） |
| 按下健檢到開始 | 約 1 分鐘（要開機） | 幾秒 |
| 適合 | 自己測、少量測試 | 給測試者用 |

### 5A. GitHub Actions（免費版，目前用這個）

1. **放 secrets**：GitHub → `repodoctor` repo → Settings → Secrets and variables → **Actions** → New repository secret，加這四個：

   | Name | 值 |
   |---|---|
   | `SUPABASE_URL` | `https://aikcewsgyetqqjbwdxbo.supabase.co` |
   | `SUPABASE_SECRET_KEY` | Supabase API Keys 頁的 secret key（`sb_secret_...`） |
   | `APP_ID` | `5881656` |
   | `APP_PRIVATE_KEY` | 用記事本打開下載的 `.pem`，整段貼上（含 BEGIN／END 那兩行） |

   （GitHub 不准 secret 名稱用 `GITHUB_` 開頭，所以叫 `APP_ID`／`APP_PRIVATE_KEY`）
2. **做一把「叫醒用」的 token**：GitHub → 頭像 → Settings → Developer settings → Personal access tokens →
   **Fine-grained tokens** → Generate new token
   - Token name：`repodoctor-kick`
   - Expiration：1 年（到期前要換新的，不然健檢會變成要等 3 小時）
   - Repository access：**Only select repositories** → 只選 `repodoctor`
   - Permissions → Repository permissions → **Actions：Read and write**（其他全部不給）
   - Generate，複製 token（只顯示一次）
3. **把 token 放進 Supabase**：Supabase → SQL Editor，貼這一行（把 `<token>` 換成剛複製的），Run：
   ```sql
   select vault.create_secret('<token>', 'github_dispatch_token');
   ```
   （存在 Supabase 的保險箱 Vault 裡，不會出現在程式碼或網站上）
4. **加叫醒鈴**：Supabase → SQL Editor，貼上 `supabase/migrations/002_kick_worker.sql` 全部內容，Run。
   接著再貼 `supabase/migrations/003_retention_and_account_deletion.sql`，Run（報告 90 天到期刪細節、「刪除我的所有資料」連帳號一起刪，都靠這一份）。
   再貼 `supabase/migrations/004_repo_sync.sql`，Run（之後到 GitHub 加 repo，「我的專案」才會跟著更新）。
5. **試跑一次**：GitHub → `repodoctor` → **Actions** → 左邊 `worker` → **Run workflow**。
   跑完是綠勾就代表連得上 Supabase 和 GitHub App。

之後有人按「開始健檢」或裝好 App，Supabase 會自動叫醒它；另外每 3 小時自動跑一次當保險。

### 5B. Render（之後要付費時照這個做）

1. https://render.com → 用 **Google** 登入（你的 Render 帳號是用 Google 註冊的）
2. New + → **Background Worker** → 選 `repodoctor` repo
3. 設定：
   - Name：`repodoctor-worker`
   - Region：**Singapore**（離 Supabase 東京機房最近）
   - Branch：`main`
   - Root Directory：`worker`
   - Runtime：Python 3
   - Build Command：`pip install -e ".[worker]"`
   - Start Command：`python runner.py`
   - Instance Type：Starter
4. Environment Variables：

   | Key | Value |
   |---|---|
   | `SUPABASE_URL` | `https://aikcewsgyetqqjbwdxbo.supabase.co` |
   | `SUPABASE_SECRET_KEY` | Supabase 的 secret key（`sb_secret_...`） |
   | `GITHUB_APP_ID` | `5881656` |
   | `GITHUB_APP_PRIVATE_KEY_PATH` | `/etc/secrets/github-app.pem` |
   | `PYTHON_VERSION` | `3.12.7` |
   | `ANTHROPIC_API_KEY` | 要開 AI 分析才填 |

5. **Secret Files** → Add：Filename `github-app.pem`，內容貼上整個 `.pem`（含 BEGIN／END）
6. Deploy，到 Logs 確認沒有紅字
7. **關掉 5A**：GitHub → `repodoctor` → Actions → `worker` → 右上「⋯」→ **Disable workflow**
   （兩邊同時開也不會出錯，資料庫保證同一筆健檢只會被搶一次，只是浪費 Actions 分鐘數）

★ 不要改用 Render 的**免費 Web Service** 代替：免費方案一個帳號每月共 750 小時，
現有的教會系統 24 小時在線就差不多用完，兩個一起跑可能連教會系統一起被停。

## 6. 試一次

1. 打開網站 → 用 GitHub 登入 → 按「安裝 GitHub App」→ 只勾一個 repo
2. 回到網站，等幾秒重新整理 → 會看到那個 repo
3. 按「開始健檢」→ 看掃描進度 → 看報告

卡住的話，看 GitHub → Actions → worker 最近一次的紀錄（用 Render 的話看 Render 的 Logs），把錯誤訊息貼給 Claude。

---

## 7. 開啟 AI 分析（登入與權限、重複、規範落差）

程式已經接好，放好金鑰就會動。金鑰**只放在健檢主機那邊**（GitHub Actions secrets；改 Render 後放 Render），
不會出現在網站上。

1. **申請金鑰**：https://console.anthropic.com → API Keys → Create Key（名字 `repodoctor`），複製 `sk-ant-...`
2. **先設花費上限**（防止意外燒錢）：Console → Settings → **Limits** → 設每月上限，例如 US$10。
   目前估一次健檢約 NT$1–7（路由多的專案貴一點），10 位測試者每人每天最多 10 次
3. **放進 GitHub**：`repodoctor` repo → Settings → Secrets and variables → Actions → New repository secret
   - Name：`ANTHROPIC_API_KEY`
   - Secret：剛複製的 `sk-ant-...`
4. **測試金鑰**：Actions → `worker` → Run workflow → 勾 **「只測試 Anthropic API 金鑰能不能用」** → Run。
   點進去看「測試 AI 金鑰」那一步：
   - 寫「AI 金鑰可以用」→ 成功（這次測試花費不到台幣 1 分錢，不送任何程式碼）
   - 寫「AI 金鑰測試失敗：……」→ 照中文原因處理（金鑰貼錯、還沒儲值等）
5. **網站打開 AI 選項**：Vercel → `repodoctor` → Settings → Environment Variables →
   `NEXT_PUBLIC_AI_ENABLED` 改成 `true` → Deployments → Redeploy
6. **試一次**：網站「我的專案」勾「加上 AI 分析」→ 開始健檢。
   報告最下面會寫這次 AI 花了多少（美金與台幣），「登入與權限」「規範落差」也會有分數

之後改用 Render：Render 的 Environment Variables 一樣加 `ANTHROPIC_API_KEY`（5B 的表格裡已經列了）。

## 這一版的限制（之後再做）

- 只支援安裝在**個人帳號**上的 GitHub App；裝在組織上的會被拒絕（要另外確認你是那個組織的成員）
- 歷史 commit 只抓最新一個（淺層 clone），所以「.env 曾經被 commit 過」這項在線上版抓不到，只有本機版抓得到
- 每人每天最多 10 次健檢（`worker/config.py` 的 `DAILY_SCANS_PER_USER`）
- 健檢細節保存 90 天（`worker/config.py` 的 `RETENTION_DAYS`，要改的話 `web/lib/legal.ts` 和隱私權政策也要一起改）
- 隱私權政策與使用條款是草稿，不是法律意見；正式收費或擴大使用前建議請律師看過。聯絡方式用 Vercel 環境變數 `NEXT_PUBLIC_CONTACT_URL` 設定（沒設就連到 GitHub 個人頁）
- 出事時怎麼辦：見 `docs/INCIDENT.md`
- 還沒有金流、白話地圖、前後比較、分享卡（SPEC Phase 2）
