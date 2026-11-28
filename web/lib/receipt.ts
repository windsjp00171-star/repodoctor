// 每次健檢的「資料處理紀錄」：把「我們怎麼處理你的程式碼」從承諾變成這一次的實際紀錄。
// 只用健檢本來就有記的資料（開始／結束時間、每次 AI 呼叫的服務商與 token），不另外蒐集。

export type ReceiptMode = "app" | "quick" | "demo";

export interface AICall { provider?: string; model?: string; input_tokens?: number; output_tokens?: number }

export interface Receipt {
  mode: ReceiptMode;
  startedAt: string | null;
  finishedAt: string | null;
  calls: AICall[];
}

const LABEL: Record<string, string> = { anthropic: "Anthropic Claude", groq: "Groq" };

/** 依服務商彙總：幾次請求、多少 token。舊的紀錄沒有 provider，用模型名稱判斷。 */
export function aiSummary(calls: AICall[]): { label: string; requests: number; tokens: number }[] {
  const by = new Map<string, { label: string; requests: number; tokens: number }>();
  for (const c of calls) {
    const p = c.provider ?? (c.model?.startsWith("claude") ? "anthropic" : "groq");
    const row = by.get(p) ?? { label: LABEL[p] ?? p, requests: 0, tokens: 0 };
    row.requests += 1;
    row.tokens += (c.input_tokens ?? 0) + (c.output_tokens ?? 0);
    by.set(p, row);
  }
  return [...by.values()];
}

export function formatTime(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleString("zh-TW", { timeZone: "Asia/Taipei", dateStyle: "medium", timeStyle: "short" });
}

export function addDays(iso: string | null, days: number): string | null {
  if (!iso) return null;
  return new Date(new Date(iso).getTime() + days * 86_400_000).toISOString();
}
