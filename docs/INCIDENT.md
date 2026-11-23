# 出事時怎麼辦（資安事件處理）

給維護者自己看的。懷疑有金鑰外洩、有人讀到不該讀的資料、或 GitHub 寄來可疑通知時，照順序做。
**先止血，再查原因，最後通知。** 不要等查清楚才換鑰匙。

## 0. 先記下時間

開一份筆記，每做一步就寫「幾點幾分、做了什麼、看到什麼」。之後要通知使用者、要回頭檢討，都靠這份。

## 1. 止血：換掉可能外洩的鑰匙

不確定是哪一把，就**全部換**。每一把都是「先產生新的 → 更新到用它的地方 → 刪掉舊的」。

| 鑰匙 | 外洩的話 | 去哪裡換 | 換完更新到 |
|---|---|---|---|
| **GitHub App 私鑰**（`.pem`） | 最嚴重：可以讀所有安裝者勾選的 repo | GitHub → Settings → Developer settings → GitHub Apps → `repodoctortw` → Private keys → Generate a new private key，再把舊的 Delete | repodoctor repo 的 Actions secret `APP_PRIVATE_KEY`（之後改 Render 的話：Secret File `github-app.pem`） |
| **Supabase secret key** | 可以讀寫整個資料庫（所有人的報告、email） | Supabase → Project Settings → API Keys → 產生新的 secret key，刪掉舊的 | Actions secret `SUPABASE_SECRET_KEY`（Render 的環境變數） |
| **叫醒鈴的 GitHub token** | 只能觸發 worker 跑一次，影響小 | GitHub → Settings → Developer settings → Fine-grained tokens → 重新產生 | Supabase SQL Editor：`select vault.update_secret((select id from vault.secrets where name = 'github_dispatch_token'), '<新 token>');` |
| **Anthropic API key** | 別人可以花你的錢 | console.anthropic.com → API Keys → 停用舊的、建立新的 | Actions secret `ANTHROPIC_API_KEY` |
| **GitHub OAuth App secret** | 可以假冒登入流程 | GitHub → OAuth Apps → Generate a new client secret | Supabase → Authentication → Providers → GitHub |

情況嚴重（例如確定資料庫被讀走）時，可以先**整個停掉**：
- GitHub → repodoctor → Actions → `worker` → `…` → Disable workflow（健檢會停，資料不會再被處理）
- GitHub App 設定頁可以暫停（Suspend）所有安裝

## 2. 查：發生了什麼

- **GitHub Actions 紀錄**：repodoctor → Actions，看有沒有你沒發起的執行、或 workflow 檔被改過（`git log .github/`）
- **GitHub App 安裝清單**：App 設定頁 → Install App / Advanced，看有沒有不認識的安裝
- **Supabase**：Logs → API / Auth，看有沒有大量讀取、從陌生 IP 來的請求
- **資料庫**：`select status, count(*) from installations group by 1;` 看有沒有被標成 active 但不該是的安裝
- **程式碼**：`git log` 看最近有沒有不是你推的 commit；檢查 secret 有沒有被寫進程式或 log

## 3. 判斷要不要通知使用者

依《個人資料保護法》第 12 條：個資被竊取、洩漏、竄改或侵害時，**查明後要通知當事人**。

需要通知：使用者的 email、GitHub 帳號、報告內容（含程式片段與檔名）可能被別人看到了。
不一定需要：鑰匙外洩但確定沒被使用（紀錄裡沒有異常讀取），且已經換掉。不確定就通知。

列出受影響的人（Supabase SQL Editor）：

```sql
select u.email, u.raw_user_meta_data->>'user_name' as github, u.created_at
from auth.users u order by u.created_at;
```

## 4. 通知範本（用 email 寄給每一位受影響的使用者）

> 主旨：RepoDoctor 資安事件通知
>
> 你好，
>
> 我們在 ○月○日 發現 RepoDoctor 發生資安事件，寫信告訴你發生了什麼事，以及我們做了哪些處理。
>
> **發生了什麼事**：（一兩句白話說明，例如「我們用來讀取 GitHub 專案的金鑰被放在一個不該公開的地方，時間約 ○ 小時」。）
>
> **可能影響的資料**：（照實列出，例如：你的 GitHub 帳號名稱與 email、你健檢過的專案名稱、健檢報告中的檔案名稱與程式片段。金鑰在報告中只保留前 4 碼。）
>
> **我們已經做的處理**：已於 ○月○日 ○時 作廢並更換所有相關金鑰；（其他處理）。
>
> **建議你可以做的事**：
> 1. 到 https://github.com/settings/installations 確認 RepoDoctor 的權限，不再使用的話可以移除。
> 2. 如果你的健檢報告曾列出外洩的金鑰而你還沒更換，請盡快到該服務的後台作廢並更換。
> 3. 想刪除你在 RepoDoctor 的所有資料，登入後在「我的專案」頁最下方按「刪除我的所有資料」。
>
> 有任何問題，可以直接回覆這封信。造成你的困擾，非常抱歉。
>
> RepoDoctor

## 5. 收尾

- 在網站首頁放一則公告（簡短說明＋已處理），至少一週
- 把筆記整理成「時間軸＋原因＋以後怎麼避免」，放在這個資料夾（`docs/incidents/日期.md`）
- 避免再發生的修正，照一般流程改程式、更新 CHANGELOG
