# RepoDoctor 上線設定（給維護者）

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

## 5. 部署 worker（Render）

1. https://render.com → New → **Background Worker** → 選 `repodoctor` repo
2. Root Directory：`worker`
3. Build Command：`pip install -e ".[worker]"`
4. Start Command：`python runner.py`
5. Environment Variables：

   | 名稱 | 值 |
   |---|---|
   | `SUPABASE_URL` | 步驟 1 |
   | `SUPABASE_SECRET_KEY` | 步驟 1 的 secret key |
   | `GITHUB_APP_ID` | 步驟 3 |
   | `GITHUB_APP_PRIVATE_KEY` | 步驟 3 的 .pem 內容（整段貼上） |
   | `ANTHROPIC_API_KEY` | 要開 AI 分析才填 |
   | `PYTHON_VERSION` | `3.12.7` |

★ Render 的 Background Worker 沒有免費方案（最便宜一個月約 US$7）。Railway 也類似。

## 6. 試一次

1. 打開網站 → 用 GitHub 登入 → 按「安裝 GitHub App」→ 只勾一個 repo
2. 回到網站，等幾秒重新整理 → 會看到那個 repo
3. 按「開始健檢」→ 看掃描進度 → 看報告

卡住的話，看 Render 上 worker 的 Logs，把錯誤訊息貼給 Claude。

---

## 這一版的限制（之後再做）

- 只支援安裝在**個人帳號**上的 GitHub App；裝在組織上的會被拒絕（要另外確認你是那個組織的成員）
- 歷史 commit 只抓最新一個（淺層 clone），所以「.env 曾經被 commit 過」這項在線上版抓不到，只有本機版抓得到
- 每人每天最多 10 次健檢（`worker/config.py` 的 `DAILY_SCANS_PER_USER`）
- 還沒有金流、白話地圖、前後比較、分享卡（SPEC Phase 2）
