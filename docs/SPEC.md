# RepoDoctor SPEC — Vibe Coder 的程式健檢醫生

2026-11-22 · 富毅

> 線上版（含架構圖與開發階段圖）：https://claude.ai/artifact/1Fed7D1Exax98mee9eFqGZ
> 本檔為交給 Claude Code 使用的版本，兩張圖已改寫成文字。

## 產品定位

**RepoDoctor（暫名）是 vibe coder 的程式健檢醫生：連上 GitHub，用中文白話告訴你專案哪裡有問題，並產生可以直接貼給 Claude Code 的修復指令。**

用 AI 生程式的門檻已經很低，真正讓新手卡住、放棄的是程式生出來之後：

- 看不懂 AI 寫了什麼，專案越改越亂
- 不知道有沒有藏著危險：金鑰推上 GitHub、資料庫權限沒鎖、路由沒有登入檢查
- 同一個功能被 AI 寫了好幾份，規範文件寫的跟程式實際做的對不上
- 不知道怎麼叫 AI 修，越修越糟

差異化有三點：繁體中文、白話優先；不自動改程式，而是教使用者「怎麼跟 AI 講」；介面要做到讓人想截圖分享的程度。

## 目標使用者

兩種人都服務，但他們在同一條成長路徑的不同階段：新手從「起步引導」進來，做出專案後自然升級到「健檢」。**第一版（MVP）只做「專案變亂的人」這一邊。**

| 使用者 | 現況 | 最需要的 | 對應模組 | 版本 |
| --- | --- | --- | --- | --- |
| 專案變亂的人 | 已有好幾個 repo，開始失控 | 知道哪裡有問題、先修哪個、怎麼叫 AI 修 | 健檢報告、修復指令、白話地圖 | MVP |
| 完全新手 | 還沒有 repo，甚至沒用過 GitHub | 怎麼開始、第一句該跟 AI 講什麼 | 起步引導、規範產生器 | 第二階段 |

報告提供「白話模式」與「進階模式」，同一份掃描結果、兩種講法。預設白話，進階模式才顯示檔案路徑、行號與技術名詞。

## MVP 範圍

MVP 交付三件事：一份健檢報告、每個問題一段修復指令、一張專案白話地圖。先支援 Python（Flask）與 JavaScript/TypeScript（Next.js）專案，以及使用 Supabase 的專案。

### 健檢項目

| 類別 | 檢查什麼 | 白話報告範例 | 嚴重度 | 檢查方式 |
| --- | --- | --- | --- | --- |
| 金鑰外洩 | API key、token、.env 被 commit | 「你的 Supabase 金鑰寫在 config.py，任何人都看得到」 | 緊急 | 規則掃描 |
| 資料庫權限 | Supabase RLS 是否開啟、service key 是否出現在前端 | 「會員資料表沒上鎖，知道網址就能讀」 | 緊急 | 規則掃描 + migration 檔解析 |
| 登入與權限 | 哪些路由沒有登入檢查、權限檢查是否各寫各的 | 「這 3 個頁面沒登入也能進」 | 高 | AI 分析 |
| 重複與散落 | 同一功能寫了好幾份、多個地方建立資料庫連線 | 「登入檢查被寫了 4 份，改一個忘了另外 3 個」 | 中 | 規則掃描 + AI 分析 |
| 規範落差 | CLAUDE.md 寫的規則 vs 程式實際寫法 | 「規範說要用 db.py，但有 2 個檔案自己建了連線」 | 中 | AI 分析 |
| 專案衛生 | 沒有 README、沒有 .gitignore、死檔案、巨大檔案 | 「這個檔案 2,000 行，AI 以後會很難改」 | 低 | 規則掃描 |

先用規則掃描拿到確定的問題，再把「需要理解程式」的部分交給 AI，這樣假警報少、token 成本也低。

### 修復指令

每個問題附一段中文指令，一鍵複製貼給 Claude Code。指令包含：要改哪些檔案、改成什麼樣子、不可以動到什麼、改完怎麼驗證。另提供「全部緊急問題」一鍵合併成一段指令。

### 白話地圖

自動產生專案結構圖：每個資料夾在做什麼、資料從哪裡進來、存到哪裡、怎麼啟動專案。

### 這版不做

- 不自動改程式、不開 PR（只讀不寫，信任門檻最低）
- 不做起步引導與規範產生器（第二階段）
- 不支援 GitLab、Bitbucket
- 不做團隊協作功能

## 使用流程

從進網站到拿到修復指令，目標是 3 分鐘內完成，不需要看任何教學。

1. 進入首頁，看到一份範例健檢報告的動態展示
2. 用 GitHub 帳號登入，安裝唯讀的 GitHub App，只勾選要健檢的 repo
3. 在儀表板選一個 repo，按「開始健檢」
4. 掃描進行中：即時顯示目前掃到哪個檔案、已發現幾個問題（這是介面的高潮，見 UI/UX 章節）
5. 看健檢報告：總分、各類別分數、依嚴重度排序的問題卡片
6. 點開問題卡：白話說明、為什麼危險、修復指令，一鍵複製
7. 修完後重新健檢，看到分數上升的動畫與前後比較
8. （可選）分享健檢成績卡，只顯示分數與類別，不含程式內容

## 技術架構

**前端用 Next.js，掃描工作交給獨立的 Python worker，兩邊只透過 Supabase 溝通。** 酷炫的動效與元件生態幾乎都在 React 這邊，Flask + Jinja 很難做到同等水準；掃描則用熟悉的 Python，也避開網頁主機的執行時間限制。

### 架構圖（文字版）

```
[Next.js 前端 / Vercel] <-- 讀寫、訂閱進度 --> [Supabase] <-- 取任務、寫結果 --> [Python 掃描 worker / Render 或 Railway]
                                              Auth：GitHub 登入                     先規則掃描，再 AI 分析
                                              Postgres，每張表開 RLS                掃完立刻刪除程式碼
                                              Realtime：掃描進度                         |
                                                                          +----------+----------+
                                                                          |                     |
                                                                 只讀程式碼 v          遮罩後的片段 v
                                                              [GitHub App]            [Claude API]
                                                              唯讀權限、淺層 clone     白話說明與修復指令
```

前端與 worker 之間沒有直接連線，所有溝通都經過 Supabase。

| 層 | 選用 | 說明 |
| --- | --- | --- |
| 前端 | Next.js（App Router）+ TypeScript | 部署在 Vercel |
| 樣式與元件 | Tailwind CSS + shadcn/ui | 見 UI/UX 章節 |
| 動效 | Motion（原 Framer Motion） | 頁面轉場、分數動畫、卡片展開 |
| 登入 | Supabase Auth（GitHub OAuth） | 登入與 GitHub App 安裝分開 |
| 資料庫 | Supabase Postgres，每張表都開 RLS | 自己的產品不能犯自己檢查的錯 |
| 即時進度 | Supabase Realtime | worker 寫入進度，前端訂閱顯示掃描動畫 |
| 掃描 worker | Python 3.12，部署在 Render 或 Railway | 輪詢 scans 表的待辦任務 |
| repo 存取 | GitHub App，權限只有 Contents: read、Metadata: read | 用安裝 token 做淺層 clone |
| AI 分析 | Claude API | 只送規則掃描挑出的片段，不送整個 repo |
| 金流 | 待定（台灣金流服務或 Stripe） | 第二階段再接 |

### 程式碼隱私原則

- clone 到暫存資料夾，掃完立刻刪除，不儲存使用者的程式碼
- 發現的金鑰只存「前 4 碼 + 檔案 + 行號」，完整值不寫進資料庫、不送給 Claude API
- 送給 Claude API 前，先把所有疑似金鑰的字串遮罩
- 隱私頁面用白話寫清楚以上三點，這是信任的關鍵

## 資料模型

MVP 只需要五張表。所有表都開 RLS，使用者只看得到自己的資料；worker 用 service role 寫入。

| 表 | 主要欄位 | 用途 |
| --- | --- | --- |
| profiles | id（對應 auth.users）、github_login、plan、report_mode（plain / advanced）、created_at | 使用者資料與方案 |
| installations | id、user_id、github_installation_id、created_at | GitHub App 安裝紀錄 |
| repos | id、user_id、installation_id、full_name、default_branch、language、last_scan_id | 使用者勾選的 repo |
| scans | id、repo_id、status（queued / running / done / failed）、progress（0–100）、current_file、score、category_scores（jsonb）、map（jsonb）、commit_sha、token_usage、started_at、finished_at | 一次健檢；progress 與 current_file 供 Realtime 訂閱 |
| findings | id、scan_id、category、severity（critical / high / medium / low）、title、plain_explanation、advanced_explanation、file_path、line、masked_snippet、fix_prompt、fingerprint | 單一問題；fingerprint 用來比較前後兩次健檢「修好了哪些」 |

## UI/UX 視覺設計規範

**視覺方向：「深色醫學影像 × 終端機」。** 像在看一台正在掃描你程式的儀器：深色底、一個鮮明的主色、細線條與網格、先進但不淺。炫的力氣集中在四個標誌時刻，其他地方安靜、好讀，這是「高級」跟「花俏」的差別。

### 四個標誌時刻（預算花在這裡）

1. **掃描動畫**：專案檔案樹以細線呈現，一道掃描光從上往下掃過；worker 每掃到一個檔案，該節點亮起，發現問題時亮起嚴重度顏色並彈出計數。進度來自 Supabase Realtime，是真的進度，不是假動畫。
2. **健康分數環**：大圓環從 0 跑到分數，數字同步跳動；環的顏色依分數從紅轉綠。下方六個類別小環依序亮起。
3. **問題卡片**：依嚴重度排列，緊急卡片邊框有流動光暈；點擊以 layout 動畫展開成詳情；「複製指令」按下後變成打勾並有微彈跳。
4. **白話地圖**：可拖曳、縮放的節點圖，資料流向線上有流動的光點；有問題的節點帶小紅點，點了直接跳到問題卡。

另外兩個加分項：重新健檢後「分數上升」的前後對比動畫，以及可分享的健檢成績卡圖片（Next.js 動態產生 OG 圖）。

### 元件與套件

| 用途 | 套件 | 用在哪裡 |
| --- | --- | --- |
| 基礎元件 | shadcn/ui | 按鈕、對話框、分頁、表單、提示 |
| 動效 | Motion | 轉場、卡片展開、分數動畫 |
| 炫效元件 | Magic UI、Aceternity UI | 流動邊框光、數字跳動、首頁聚光燈與背景網格 |
| 節點圖 | React Flow（@xyflow/react） | 白話地圖 |
| 圖示 | Lucide | 全站統一 |
| 程式碼顯示 | Shiki | 進階模式的程式片段 |

炫效元件一律是「複製進專案再改」的形式，要改成本站的顏色與節奏，不要原樣貼上，不然會看起來跟其他一堆網站一模一樣。

### 設計 token（初稿）

| token | 深色（預設） | 用途 |
| --- | --- | --- |
| background | #0A0E14 | 頁面底 |
| surface | #111821 | 卡片、面板 |
| border | #1F2A37 | 細線、網格 |
| text | #E6EDF3 | 主文字 |
| text-muted | #8B98A9 | 次要文字 |
| primary | #22D3EE（電光青） | 掃描光、主要按鈕、選中狀態 |
| critical | #F43F5E | 緊急 |
| high | #F59E0B | 高 |
| medium | #EAB308 | 中 |
| healthy | #34D399 | 健康、修復完成 |

字型：中文 Noto Sans TC，英文與數字 Inter，程式與分數 JetBrains Mono。中文字型檔很大，用 next/font 載入並開啟切割。圓角 12px，間距以 4px 為單位。淺色模式第二階段再做。

### 頁面清單

| 頁面 | 重點 |
| --- | --- |
| 首頁 | 一句話標語 + 範例報告的自動播放展示 + 「用 GitHub 登入」；不登入也能看到完整範例 |
| 儀表板 | 所有 repo 的健康分數卡片、上次健檢時間、一鍵健檢 |
| 掃描中 | 標誌時刻 1 |
| 健檢報告 | 標誌時刻 2、3；白話／進階切換；「全部緊急問題」合併指令 |
| 白話地圖 | 標誌時刻 4 |
| 方案與定價 | 三欄方案比較 |
| 隱私說明 | 白話說明程式碼怎麼處理 |

### 底線規則

- 尊重「減少動態效果」系統設定（prefers-reduced-motion）：動畫全部改成淡入
- 文字對比達 WCAG AA；嚴重度不只靠顏色，也要有文字與圖示
- 手機版完整可用，報告頁在 375px 寬也要好讀
- 首頁 LCP 小於 2.5 秒；重的動效元件延遲載入

## Claude Code 開發規範與建議 skill

**前端要漂亮，關鍵是讓 Claude Code「看得到自己做出來的畫面」，而不是只寫程式不看結果。**

### 建議搭配

| 工具 | 用途 | 什麼時候用 |
| --- | --- | --- |
| Anthropic 官方 frontend-design plugin | 讓 Claude Code 做出有設計感、不像範本的介面 | 每次做新頁面或改版面 |
| Playwright MCP | 開瀏覽器截圖，自己檢查畫面、手機版、動畫 | 每做完一頁就截圖自我審查 |
| Context7 MCP | 查 Next.js、shadcn/ui、Motion 最新文件 | 避免 AI 用過時的寫法 |
| shadcn CLI | 加入元件 | 需要新元件時 |
| Supabase MCP | 建表、設 RLS、跑安全建議檢查 | 資料模型階段 |
| Vercel MCP | 部署、看錯誤日誌 | 上線與除錯 |

### 建議的設計流程

1. 先在 Claude 上用 Design 畫出首頁、掃描中、健檢報告三張畫面，比較幾個版本、定下風格
2. 把定稿的設計 token 寫進 globals.css 與 Tailwind 設定
3. Claude Code 依定稿一頁一頁做，每頁做完用 Playwright 截圖（桌機 1440px、手機 375px）對照定稿
4. 標誌時刻的動畫最後做，一次只做一個

### 專案 CLAUDE.md 規則

- 前端只在 lib/supabase/client.ts 與 lib/supabase/server.ts 建立 Supabase client，其他地方一律 import
- service role key 只能出現在 worker，絕不能出現在前端任何檔案
- worker 端：只在 db.py 建立 Supabase client，一律 `from db import supabase`
- 登入保護只在 middleware.ts 統一處理，頁面裡不各自寫登入檢查
- 顏色、圓角、間距只用設計 token，元件裡不出現寫死的色碼
- 動畫參數集中在 lib/motion.ts，全站共用同一組節奏
- 所有介面文字使用繁體中文，集中放在文案檔，方便之後改寫

這份 CLAUDE.md 本身就是「規範產生器」要產出的東西的範本，也是健檢「規範落差」項目的第一個測試對象。

## 定價與成本估算

**免費版讓人看見問題，付費版幫人解決問題。** 以下金額都是初稿，等 Phase 0 實測每次健檢的成本後再定。

| 方案 | 價格（初稿） | 內容 |
| --- | --- | --- |
| 免費 | NT$0 | 1 個 repo、每月 2 次健檢、完整問題清單、前 3 個問題附修復指令 |
| Pro | NT$199／月 | 10 個 repo、每月 30 次健檢、全部修復指令、白話地圖、前後比較 |
| 課程學員 | 購課送 Pro 3 個月 | 與 Vibe Coding 實戰課互相導流 |

### 成本

- **AI 成本**：目標是每次健檢 NT$5 以內。做法是規則掃描先篩、只送片段；白話說明用較便宜的模型，只有「登入與權限」這類要懂邏輯的分析才用強模型。每次健檢把 token 用量寫進 scans.token_usage，從第一天就看得到真實成本。
- **主機成本**：Vercel 免費方案只限非商業用途，開始收費後要升級；Supabase 和 worker 主機也有月費。各家價格上線前要到官網確認。
- **損益平衡**：等實測數字出來，算「主機月費 ÷ 每個 Pro 毛利」就知道要幾個付費使用者。

## 開發階段與驗收標準

**酷炫介面放在 Phase 1 才開始做；Phase 0 先確認健檢引擎準不準、成本多少。** 每個階段過了關卡才進下一個，關卡數字是建議值，可以再調。

1. **Phase 0　驗證健檢引擎（不做介面）**
    - Python worker 跑規則掃描加 Claude 分析，輸出 JSON 報告
    - 用自己的 10 個 repo 當測試資料，記錄每次健檢的 token 成本
    - 關卡：緊急問題零漏抓，假警報看了覺得可以接受
2. **Phase 1　MVP 健檢網站**
    - GitHub 登入、選 repo、掃描動畫、健檢報告、修復指令
    - 找 10 位測試者（課程學員優先）免費使用
    - 關卡：至少一半測試者照指令修好一個問題
3. **Phase 2　付費與完整體驗**
    - 金流、Pro 方案、白話地圖、前後比較、健檢成績分享卡
    - 淺色模式與手機版細修
    - 關卡：有第一批付費使用者，AI 成本在預算內
4. **Phase 3　新手入口**
    - 起步引導、規範產生器（免費）、與 Vibe Coding 實戰課串接
    - 公開 repo 貼網址就能健檢，當作引流

交給 Claude Code 時，一次只給一個階段，從 Phase 0 開始。

## 風險與待決事項

**最大的風險是健檢不準：假警報太多，使用者就不再相信報告。** 所以 Phase 0 先用自己的 repo 驗證準確度，再投入介面。

| 風險 | 影響 | 應對 |
| --- | --- | --- |
| 假警報多 | 使用者不信任報告 | 規則掃描優先；每個問題可按「這不是問題」，回饋用來調整規則 |
| 使用者不敢給程式碼 | 沒人安裝 | 只讀權限、不存程式碼、隱私頁白話說明；首頁不登入就能看範例報告 |
| 大工具已有類似功能 | 難以差異化 | GitHub 本身有金鑰掃描，也有英文 AI 程式審查工具；我們的切入點是中文白話、新手、教使用者怎麼跟 AI 講 |
| AI 成本失控 | 免費版越多越虧 | 免費版限次數、大型 repo 只掃重點目錄、監控 token_usage |
| 技術棧轉換 | 對 Next.js 不如 Flask 熟 | 前端主要交給 Claude Code，人負責規範與驗收；worker 仍是 Python |

### 待決事項

- [ ] 產品名稱：RepoDoctor 是暫名，要查網域與同名產品；是否放在 EmmArk 品牌之下？
- [ ] 金流：台灣金流服務還是 Stripe？
- [ ] 第一批測試者：課程學員還是公開招募？
- [ ] 是否也掃公開 repo，用「貼網址就能健檢」當引流？
