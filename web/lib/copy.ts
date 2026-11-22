// 所有介面文字集中在這裡（SPEC：繁體中文、集中放在文案檔，方便之後改寫）。

export const copy = {
  brand: "RepoDoctor",
  tagline: "你的程式健檢醫生",
  intro: "選一個專案，按「開始健檢」。幾秒鐘後，你會知道哪裡有危險、先修哪個，以及可以直接貼給 Claude Code 的修復指令。",
  projects: {
    title: "你的專案",
    empty: "在這台電腦上找不到專案資料夾。請在下面輸入路徑。",
    lastScan: "上次健檢",
    never: "還沒健檢過",
    start: "開始健檢",
    view: "看報告",
    custom: "其他資料夾",
    customPlaceholder: "/home/you/my-project",
  },
  ai: {
    label: "加上 AI 分析（登入與權限、重複、規範落差）",
    noKey: "要設定 ANTHROPIC_API_KEY 才能用 AI 分析。現在只跑規則掃描，不花錢。",
    hint: "每次大約 NT$1–7，依專案大小而定。",
  },
  scanning: {
    title: "掃描中",
    found: "已發現問題",
    files: "最近掃過的檔案",
    failed: "健檢失敗",
  },
  report: {
    score: "健康分數",
    back: "回到專案列表",
    rescan: "重新健檢",
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
    badPath: "找不到這個資料夾",
    notFound: "找不到這次健檢",
    workerFailed: "健檢引擎執行失敗，請看下面的訊息",
  },
};

export const allCriticalPrompt = (project: string, prompts: string[]) =>
  `以下是 RepoDoctor 對 ${project} 找到的 ${prompts.length} 個緊急問題。請一個一個處理，每處理完一個先停下來讓我確認，再做下一個。\n\n` +
  prompts.map((p, i) => `── 第 ${i + 1} 個 ──\n${p}`).join("\n\n");
