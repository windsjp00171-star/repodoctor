// 所有介面文字集中在這裡（SPEC：繁體中文、集中放在文案檔，方便之後改寫）。

export const copy = {
  brand: "RepoDoctor",
  tagline: "你的程式健檢醫生",
  intro: "選一個專案，按「開始健檢」。幾秒鐘後，你會知道哪裡有危險、先修哪個，以及可以直接貼給 Claude Code 的修復指令。",
  landing: {
    headline: "用 AI 寫的程式，交給 RepoDoctor 健檢",
    sub: "連上 GitHub，用中文白話告訴你專案哪裡有危險：金鑰外洩、資料表沒上鎖、頁面沒登入也能進。每個問題附一段可以直接貼給 Claude Code 的修復指令。",
    cta: "免費健檢我的專案",
    ctaNote: "用 GitHub 帳號登入，三步驟完成，不用安裝任何東西。",
    dashboard: "到我的專案",
    securityLink: "我們怎麼保護你的程式碼 →",
    demo: "先看範例報告（不用登入）",
    coverageTitle: "檢查什麼、支援什麼",
    coverage: [
      {
        title: "規則掃描（免費，不送 AI）",
        items: [
          "金鑰外洩：OpenAI、Anthropic、Groq、Google、GitHub、AWS、Stripe、Slack、Supabase secret key、私鑰，以及變數名像金鑰的值",
          ".env 被 commit 進 git、.gitignore 沒擋 .env",
          "Supabase：資料表沒開 RLS、service role key 出現在前端",
          "資料庫連線散落在多個檔案、登入檢查寫了好幾份",
          "專案衛生：沒有 README、超長檔案、巨大檔案、備份檔",
        ],
      },
      {
        title: "AI 分析（你勾選才會跑）",
        items: [
          "登入與權限：哪些頁面或 API 沒登入也能進",
          "重複程式：同一件事寫了好幾份",
          "規範落差：CLAUDE.md / AGENTS.md 寫的規則，程式有沒有照做",
        ],
      },
      {
        title: "支援的技術",
        items: [
          "語言：Python、JavaScript、TypeScript（含 .jsx / .tsx / .vue / .svelte），SQL migration",
          "框架：Next.js（App Router、pages/api、middleware）、Flask、Django、Express、Vercel serverless",
          "資料庫：Supabase（其他資料庫目前只檢查金鑰和連線散落）",
          "只支援 GitHub 上的 repo，個人帳號；組織帳號之後支援",
        ],
      },
    ],
    privacyTitle: "你的程式碼怎麼處理",
    privacy: [
      "只要唯讀權限，而且只看你勾選的 repo。我們不能改你的程式，也不會開 PR。",
      "健檢時把程式下載到暫存資料夾，掃完立刻刪除，不保存你的程式碼。",
      "找到的金鑰只記前 4 碼和位置，完整的值不存、也不送給 AI。",
    ],
  },
  improve: {
    landingTitle: "不只是健檢：我們陪你把程式越改越好",
    landingSteps: [
      { title: "找出問題，排好先後", body: "最危險的排最前面。看不懂程式也沒關係，每個問題都用白話說明。" },
      { title: "一鍵複製，交給 AI 修", body: "每個問題附一段寫好的指令：要改哪裡、不能動什麼、怎麼驗證。貼給 Claude Code 就能修。" },
      { title: "重新健檢，看見進步", body: "修完再健檢一次，告訴你分數升了多少、哪幾個真的修好了。" },
      { title: "寫進規則，以後不再犯", body: "把對應的規則加進 CLAUDE.md，AI 下次寫程式就會照著做，同樣的問題不會再出現。" },
    ],
    progressTitle: "上次以來的進步",
    progressNone: "修完之後按右上角「重新健檢」，這裡會告訴你修好了哪幾個、分數升了多少。",
    fixed: "修好了",
    added: "新出現",
    remaining: "還沒修",
    nextTitle: "接下來怎麼做",
    nextCritical: (n: number) => `先處理 ${n} 個緊急問題：按下面的「複製全部緊急問題的指令」，貼給 Claude Code，一個一個修。`,
    nextHigh: (n: number) => `沒有緊急問題了，接著處理 ${n} 個「高」等級的問題。`,
    nextRest: "剩下的都是中、低等級，可以慢慢改；先挑你最常改的檔案下手。",
    nextClean: "這次沒有發現問題。之後每次大改完都可以再健檢一次。",
    nextRescan: "修完一批就按「重新健檢」，確認真的修好、也沒有改出新問題。",
    directionTitle: "改善方向：你最該加強的地方",
    directionSub: "把下面的規則加進專案的 CLAUDE.md（沒有就新建一個），AI 以後寫程式會照著做，同樣的問題不會再出現。",
    copyRules: "複製這些規則",
    rulesHeader: "## RepoDoctor 建議的規則",
    directions: {
      secrets: {
        why: "金鑰一旦進了 git，就算刪掉，舊紀錄裡還找得到。",
        goal: "所有金鑰放在環境變數（.env），程式只用名字去讀；.env 永遠不進 git。",
        rule: "- 金鑰、token、密碼一律從環境變數讀取，不准寫死在程式、設定檔、測試或註解裡；新增金鑰時同步在 .env.example 加上變數名（不放值）。",
      },
      database: {
        why: "沒上鎖的資料表，只要知道網址和公開金鑰，任何人都能讀寫。",
        goal: "每張資料表都開 Row Level Security；最高權限的金鑰只放在伺服器端。",
        rule: "- 新增 Supabase 資料表時，同一個 migration 裡一定要 ENABLE ROW LEVEL SECURITY；service role／secret key 只能出現在伺服器端程式。",
      },
      auth: {
        why: "登入檢查散在各頁面，新頁面很容易忘記加。",
        goal: "登入和權限檢查集中在一個地方（middleware 或 decorator），每個新頁面都套同一個。",
        rule: "- 登入與權限檢查只用專案統一的 decorator／middleware，不准在頁面裡各自手寫；新增路由時先說明它需不需要登入。",
      },
      duplication: {
        why: "同一件事寫了好幾份，改了一份會忘了另外幾份。",
        goal: "同一件事只寫一份，其他地方 import；資料庫連線只在一個檔案建立。",
        rule: "- 資料庫 client 只在一個檔案建立，其他地方一律 import；新增功能前先搜尋專案裡有沒有現成的寫法，有就沿用。",
      },
      drift: {
        why: "規範寫的和程式實際做的不一樣，AI 會不知道該照哪個。",
        goal: "讓 CLAUDE.md 和程式保持一致；規則改了，程式要跟上。",
        rule: "- 修改程式前先讀 CLAUDE.md；發現規則和現況不一致時先停下來告訴我，不要自己挑一種。",
      },
      hygiene: {
        why: "檔案太長、說明不全，AI 每次都要讀一大堆，越改越容易出錯。",
        goal: "保持 README、.gitignore 完整；單一檔案不要太長。",
        rule: "- 單一檔案超過 800 行時，先提出拆分方案等我確認；新增環境變數時同步更新 README 與 .env.example。",
      },
    } as Record<string, { why: string; goal: string; rule: string }>,
  },
  login: {
    title: "登入 RepoDoctor",
    sub: "用 GitHub 帳號登入。登入只會讀你的帳號名稱、頭像和 email，碰不到任何 repo。",
    button: "用 GitHub 登入",
    error: "登入沒有成功，請再試一次。",
    agreeBefore: "登入即表示你同意",
    agreeAnd: "和",
  },
  dashboard: {
    title: "我的專案",
    logout: "登出",
    installTitle: "最後一步：選一個要健檢的專案",
    installSub: "按下按鈕會到 GitHub 的頁面。照著做，大約 30 秒：",
    installSteps: [
      { title: "選「Only select repositories」", body: "只讓我們看你選的專案，其他的我們完全看不到。" },
      { title: "在下拉選單選一個專案", body: "之後想加、想移除都可以再改。" },
      { title: "按綠色的「Install」", body: "畫面上寫的「Read access to code」就是唯讀：我們只能看、不能改。" },
    ],
    install: "前往 GitHub 選專案",
    installSecurity: "為什麼這樣是安全的？",
    manage: "新增或調整可以健檢的 repo",
    pending: "正在跟 GitHub 確認……這一頁會自己更新，通常一兩分鐘。",
    syncing: "正在從 GitHub 更新可以健檢的 repo……這一頁會自己更新，通常一兩分鐘（健檢主機需要一點時間啟動）。",
    rejected: "這個安裝沒有通過確認：",
    noRepos: "還沒有可以健檢的 repo。安裝 App 時記得勾選 repo。",
    queued: "排隊中",
    running: "健檢中",
    failed: "上次失敗",
    security: "隱私與安全",
    deleteTitle: "刪除我的所有資料",
    deleteBody: "會刪掉你在 RepoDoctor 的帳號（含 email）、所有健檢紀錄、找到的問題和專案清單，幾分鐘內完成，無法復原。",
    deleteConfirm: "確定刪除",
    deleteCancel: "取消",
    deleted: "已經收到刪除要求，你的帳號和所有資料會在幾分鐘內刪除，你也已經登出。最後一步：到 GitHub 移除 RepoDoctor App，我們就連讀都讀不到了。",
    uninstall: "到 GitHub 移除 App →",
  },
  security: {
    title: "隱私與安全",
    lede: "你把程式碼交給我們健檢，我們用下面這些方式保護它。每一條都是程式實際的做法，不是口號。",
    sections: [
      {
        title: "我們拿到的權限：只能讀，不能改",
        items: [
          "GitHub App 只申請兩個權限：讀程式碼（Contents: Read-only）和讀基本資料（Metadata: Read-only）。GitHub 會在安裝頁上列給你看。",
          "我們沒辦法修改你的程式、沒辦法開 PR、沒辦法刪除任何東西——不是「不會」，是 GitHub 不給這個權限。",
          "只看得到你安裝時勾選的專案，其他專案我們完全看不到。",
          "「用 GitHub 登入」只讀你的帳號名稱、頭像和 email，碰不到任何 repo。",
        ],
      },
      {
        title: "你的程式碼：用完就刪",
        items: [
          "健檢時，程式碼被下載到一台臨時的機器，只下載最新的版本。",
          "健檢一結束，程式碼立刻刪除；目前那台臨時機器本身也會在健檢後被銷毀。",
          "我們的資料庫裡沒有你的程式碼。",
          "下載用的 GitHub 通行證效期只有 1 小時，而且只在下載那一刻使用。",
        ],
      },
      {
        title: "我們存了什麼",
        items: [
          "健檢報告：分數、找到的問題、說明和修復指令。",
          "每個問題的檔案名稱、行號，以及那一行的程式碼片段。片段裡如果有金鑰，只留前 4 碼，其餘遮掉。",
          "你的 GitHub 帳號名稱和你勾選的專案名稱。",
          "每個人只看得到自己的資料，資料庫每張表都有上鎖（Row Level Security），連別的使用者用技術手段也讀不到。",
        ],
      },
      {
        title: "資料流向：哪些只在健檢主機上跑、哪些會送給 AI",
        items: [
          "規則掃描（金鑰、資料表權限、專案衛生、連線散落）全部在我們的臨時健檢主機上跑，程式碼不會送去任何第三方。沒勾 AI 分析，就只有這一段。",
          "勾了 AI 分析，才會把挑出來的片段送出去：路由與登入檢查的開頭幾行送 Anthropic Claude API（判斷登入與權限）；疑似重複的函式、CLAUDE.md 規範內容送 Groq（判斷重複與規範落差）。不送整個專案。",
          "送出前，所有疑似金鑰的字串都會被遮掉，連前 4 碼都不留；送出前還會再檢查一次，發現漏網的就整個中止。",
          "放金鑰的檔案（例如 .env）完全不送。",
          "想完全在自己電腦上跑也可以：健檢引擎是開源的，下載後執行 python -m cli 你的資料夾 --no-ai，什麼都不會送出去。",
        ],
      },
      {
        title: "可以只授權一個 repo",
        items: [
          "安裝 GitHub App 時選「Only select repositories」，只勾你想健檢的那一個；其他 repo 我們完全看不到。",
          "之後隨時可以在「我的專案」按「新增或調整可以健檢的 repo」加減。",
        ],
      },
      {
        title: "你隨時可以收回",
        items: [
          "到 GitHub 移除 RepoDoctor App，我們立刻失去讀取權限。",
          "在「我的專案」頁最下面按「刪除我的所有資料」，你的帳號（含 email）和所有健檢紀錄會在幾分鐘內全部刪除。",
        ],
      },
    ],
    limitsTitle: "我們做不到的事，也先說清楚",
    limits: [
      "健檢報告會提到你程式裡的問題（例如哪個檔案有金鑰），這些報告存在我們的資料庫，只有你看得到；問題細節保存 90 天後自動刪除，只留分數。",
      "我們使用的服務：Supabase（資料庫，東京）、Vercel（網站）、GitHub Actions（健檢主機）；開啟 AI 分析時另外使用 Anthropic Claude API 與 Groq。",
      "這是測試中的服務，如果你的專案有非常敏感的內容，建議先用一個不重要的專案試試看。",
    ],
    back: "← 回首頁",
  },
  demo: {
    badge: "範例報告",
    note: "這是用虛構專案做的示範，內容和登入後拿到的報告一模一樣。複製按鈕都可以按。",
    cta: "健檢我自己的專案",
  },
  projects: {
    lastScan: "上次健檢",
    never: "還沒健檢過",
    start: "開始健檢",
    view: "看報告",
  },
  ai: {
    label: "加上 AI 分析（登入與權限、重複、規範落差）",
    noKey: "AI 分析還沒開放，目前只跑規則掃描。",
    hint: "AI 分析需要多等一兩分鐘。",
  },
  scanning: {
    title: "掃描中",
    queued: "排隊中：健檢主機正在啟動，通常一兩分鐘內開始。這一頁會自己更新，不用重新整理。",
    found: "已發現問題",
    files: "最近掃過的檔案",
    failed: "健檢失敗",
  },
  report: {
    score: "健康分數",
    back: "回到專案列表",
    rescan: "重新健檢",
    expired: "這份報告超過 90 天，問題細節已依保存期限刪除，只保留分數。想看現在的狀況，重新健檢一次就好。",
    plain: "白話",
    advanced: "進階",
    fix: "貼給 Claude Code 的修復指令",
    copy: "複製指令",
    copied: "已複製",
    copyFallback: "已選取，請按複製",
    allCritical: "複製全部緊急問題的指令",
    noFindings: "這一次沒有發現問題。",
    needsAi: "需要 AI",
    notApplicable: "不適用",
    rulesOnly: "只有規則",
    cost: "這次健檢的 AI 成本",
    free: "這次只跑規則掃描，沒有花錢。",
    keyNote: "報告裡的金鑰只顯示前 4 碼。「資料庫權限」只看專案裡的 SQL 檔，看不到線上資料庫。",
    scoreNote: "分數公式是初稿：緊急扣 40、高扣 20、中扣 8、低扣 3；有緊急問題總分最高 59。",
  },
  categories: {
    secrets: "金鑰外洩",
    database: "資料庫權限",
    auth: "登入與權限",
    duplication: "重複與散落",
    drift: "規範落差",
    hygiene: "專案衛生",
  } as Record<string, string>,
  severities: { critical: "緊急", high: "高", medium: "中", low: "低" } as Record<string, string>,
  errors: {
    notFound: "找不到這次健檢",
    workerFailed: "健檢沒有完成",
    startFailed: "沒辦法開始健檢，請重新整理後再試一次。",
    deleteFailed: "刪除沒有成功，請重新整理後再試一次。",
  },
};

/** 貼給 AI 的修復指令前面加上這次健檢的分數，讓它知道整體狀況、先修哪一類（沒檢查的類別不列，不要讓它以為是 0 分）。 */
export function scoreContext(r: { project: string; score: number | null; category_scores: Record<string, number | null>;
  summary: Record<string, number> }): string {
  const cats = Object.entries(copy.categories)
    .filter(([k]) => r.category_scores[k] != null)
    .map(([k, label]) => `${label} ${r.category_scores[k]}`);
  const sev = ["critical", "high", "medium", "low"].map((k) => `${copy.severities[k]} ${r.summary[k] ?? 0}`).join("・");
  return [
    `【RepoDoctor 健檢背景】${r.project}`,
    `總分 ${r.score ?? "—"} / 100（${sev}）`,
    cats.length ? `各類別分數：${cats.join("、")}` : null,
    "分數越低的類別越需要優先處理；修完後我會重新健檢，看分數有沒有進步。",
  ].filter(Boolean).join("\n");
}

export const withScore = (context: string, prompt: string) => `${context}\n\n── 這次要修的問題 ──\n${prompt}`;

export const allCriticalPrompt = (context: string, prompts: string[]) =>
  `${context}\n\n以下是 ${prompts.length} 個緊急問題。請一個一個處理，每處理完一個先停下來讓我確認，再做下一個。\n\n` +
  prompts.map((p, i) => `── 第 ${i + 1} 個 ──\n${p}`).join("\n\n");
