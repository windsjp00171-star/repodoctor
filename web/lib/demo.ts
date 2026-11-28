// 範例報告（/demo，免登入）用的假資料。
// ★ 全部是虛構的：專案名、檔名、金鑰前 4 碼都不對應任何真的 repo（CLAUDE.md：示範一律用假資料）。
// 內容照健檢引擎真的會產生的樣子寫（標題、白話說明、修復指令的格式），訪客看到的就是登入後會拿到的東西。
import type { Previous } from "./improve";
import type { Receipt } from "./receipt";
import type { Finding, Report } from "./types";

const f = (x: Omit<Finding, "id">, i: number): Finding => ({ id: `demo-${i}`, ...x });

const findings: Finding[] = ([
  {
    category: "secrets", severity: "critical", source: "rule", fingerprint: "demo-secret-openai",
    title: "OpenAI API key 寫死在 route.ts",
    plain_explanation: "你的 OpenAI 金鑰直接寫在程式裡，而且已經被 commit 進 git。任何看得到這個 repo 的人都能拿去用，帳單會算在你頭上。",
    advanced_explanation: "在 `app/api/chat/route.ts` 第 6 行找到符合 OpenAI key 格式的字串（`sk-p` 開頭）。即使刪掉這一行，舊的 commit 裡還找得到，必須到 OpenAI 後台作廢這把金鑰。",
    file_path: "app/api/chat/route.ts", line: 6,
    masked_snippet: 'const openai = new OpenAI({ apiKey: "sk-p••••••••••••" });',
    fix_prompt: "在 app/api/chat/route.ts 第 6 行，OpenAI API key 被寫死在程式裡。\n請幫我：\n1. 改成從環境變數 OPENAI_API_KEY 讀取（process.env.OPENAI_API_KEY），沒有設定時丟出清楚的錯誤\n2. 在 .env.example 加上 OPENAI_API_KEY=（不要放值）\n3. 確認 .gitignore 有擋 .env\n不要改動這個檔案的其他邏輯。改完後告訴我要到 OpenAI 後台作廢舊金鑰、產生新的。",
  },
  {
    category: "database", severity: "critical", source: "rule", fingerprint: "demo-rls-missing",
    title: "2 張資料表沒有上鎖",
    plain_explanation: "todos 和 profiles 這兩張資料表沒有開 Row Level Security。只要有人拿到網站上公開的 Supabase 網址和金鑰，就能讀寫所有人的資料。",
    advanced_explanation: "在 `supabase/migrations/20260301_init.sql` 建立了 `todos`、`profiles`，但整個專案找不到對它們的 `enable row level security`。",
    file_path: "supabase/migrations/20260301_init.sql", line: 3,
    masked_snippet: "create table public.todos (",
    fix_prompt: "todos 和 profiles 兩張 Supabase 資料表沒有開 Row Level Security。\n請新增一個 migration：\n1. 兩張表都 ENABLE ROW LEVEL SECURITY\n2. 加上 policy：使用者只能讀寫 user_id = auth.uid() 的資料\n3. 不要修改既有的 migration 檔\n寫完後列出每條 policy 的白話說明，讓我確認權限是對的。",
  },
  {
    category: "auth", severity: "high", source: "ai", fingerprint: "demo-auth-admin-api",
    title: "/api/admin/users 沒登入也能呼叫",
    plain_explanation: "這個 API 會回傳所有使用者的 email，但它沒有檢查呼叫的人有沒有登入、是不是管理員。知道網址的人都能把名單拿走。",
    advanced_explanation: "`app/api/admin/users/route.ts` 的 GET handler 直接查詢 profiles 並回傳，沒有讀取 session；`middleware.ts` 的 matcher 也沒有包含 `/api/admin`。",
    file_path: "app/api/admin/users/route.ts", line: 4,
    masked_snippet: "export async function GET() {",
    fix_prompt: "app/api/admin/users/route.ts 的 GET 沒有檢查登入與管理員權限。\n請幫我：\n1. 在 middleware.ts 的 matcher 加上 /api/admin/:path*，沒登入回 401\n2. 在這支 API 裡確認使用者是管理員，不是就回 403\n3. 不要在每支 API 各自手寫登入檢查，用專案統一的寫法\n改完後告訴我怎麼用瀏覽器無痕視窗驗證「沒登入真的進不去」。",
  },
  {
    category: "duplication", severity: "medium", source: "rule", fingerprint: "demo-dup-client",
    title: "資料庫連線在 3 個地方各自建立",
    plain_explanation: "Supabase 的連線在 3 個檔案各寫了一份。哪天要換設定，很容易改了一份、忘了另外兩份。",
    advanced_explanation: "`createClient(` 出現在 `app/page.tsx`、`app/todos/actions.ts`、`components/TodoList.tsx`；建議集中到 `lib/supabase/client.ts`（瀏覽器）與 `lib/supabase/server.ts`（伺服器）。",
    file_path: "components/TodoList.tsx", line: 9,
    masked_snippet: "const supabase = createClient(url, anonKey);",
    fix_prompt: "Supabase client 在 app/page.tsx、app/todos/actions.ts、components/TodoList.tsx 各自建立。\n請幫我：\n1. 建立 lib/supabase/client.ts（瀏覽器用）和 lib/supabase/server.ts（伺服器用）\n2. 三個檔案都改成 import 這兩支\n3. 行為不要改變\n改完後列出改了哪些檔案。",
  },
  {
    category: "hygiene", severity: "medium", source: "rule", fingerprint: "demo-gitignore-env",
    title: ".gitignore 沒有擋 .env",
    plain_explanation: "專案有用到 .env 放金鑰，但 .gitignore 沒有排除它。下次不小心 git add . 就會把所有金鑰一起推上去。",
    advanced_explanation: "`.gitignore` 存在，但沒有任何一行符合 `.env`；程式中有 6 處讀取 `process.env`。",
    file_path: ".gitignore", line: null, masked_snippet: null,
    fix_prompt: "請在 .gitignore 加上：\n.env\n.env*.local\n並確認 .env.example 沒有被擋到（它要進 git）。然後用 git status 檢查目前有沒有 .env 已經被追蹤，有的話告訴我怎麼移除追蹤（不要刪掉檔案本身）。",
  },
  {
    category: "hygiene", severity: "low", source: "rule", fingerprint: "demo-long-file",
    title: "page.tsx 有 1,240 行",
    plain_explanation: "這個檔案太長了。AI 每次改它都要讀一大堆，越改越容易出錯，也很難找到要改的地方。",
    advanced_explanation: "`app/dashboard/page.tsx` 共 1,240 行，裡面有 14 個元件定義。",
    file_path: "app/dashboard/page.tsx", line: null, masked_snippet: null,
    fix_prompt: "app/dashboard/page.tsx 有 1,240 行。請先不要改程式，提出一個拆分方案：要拆成哪幾個元件檔、各放在哪裡、每個大概多少行。我確認後再動手。",
  },
] satisfies Omit<Finding, "id">[]).map(f);

export const demoReport: Report = {
  project: "demo-user/todo-app",
  score: 52,  // 有緊急問題時總分最高 59（跟報告頁底下寫的公式一致）
  category_scores: { secrets: 40, database: 50, auth: 70, duplication: 80, drift: null, hygiene: 85 },
  summary: { critical: 2, high: 1, medium: 2, low: 1 },
  coverage: {
    auth: { status: "done", note: "" },
    duplication: { status: "done", note: "" },
    drift: { status: "not_applicable", note: "沒有 CLAUDE.md / AGENTS.md 之類的規範檔" },
  },
  findings,
  files_scanned: 86,
  languages: ["TypeScript", "SQL"],
  cost: { input_tokens: 18_420, output_tokens: 2_310, cost_usd: 0.0381, cost_twd: 1.22 },
};

// 「上次以來的進步」：上一次比這次多一個問題（已經修好），讓訪客看到改善循環長什麼樣子。
export const demoPrevious: Previous = {
  score: 41,
  created_at: "2026-11-20T09:30:00Z",
  findings: [
    { fingerprint: "demo-secret-service-role", title: "前端檔案 lib/supabase.ts 用到 service role key", severity: "critical" },
    ...findings.map(({ fingerprint, title, severity }) => ({ fingerprint, title, severity })),
  ],
};

export const demoReceipt: Receipt = {
  mode: "demo",
  startedAt: "2026-11-24T09:30:05Z",
  finishedAt: "2026-11-24T09:31:48Z",
  calls: [
    { provider: "anthropic", input_tokens: 15_200, output_tokens: 1_900 },
    { provider: "groq", input_tokens: 3_220, output_tokens: 410 },
  ],
};
