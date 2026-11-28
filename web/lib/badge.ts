// 健檢徽章的 SVG（貼在別人的 README／網站上，所以不能用我們網站的 CSS 變數，顏色只能寫在這裡）。
import { copy } from "./copy";

const COLORS = { label: "#24292f", pass: "#2ea44f", neutral: "#8b949e" };

// 粗估文字寬度：中文字約 12px、英數約 7px（11px 字級）
const textWidth = (s: string) => [...s].reduce((w, c) => w + (c.charCodeAt(0) > 0x2e80 ? 12 : 7), 0);
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

export type BadgeStatus = { score: number | null; has_critical: boolean } | null;

/** 只看分數和有沒有緊急問題；問題內容永遠不出現在徽章上。 */
export function badgeText(s: BadgeStatus): { text: string; color: string } {
  const b = copy.badge;
  if (!s || s.score == null) return { text: b.none, color: COLORS.neutral };
  if (s.has_critical) return { text: b.notYet, color: COLORS.neutral };
  return { text: `${b.passed} · ${s.score}`, color: COLORS.pass };
}

export function badgeSvg(s: BadgeStatus): string {
  const label = "RepoDoctor";
  const { text, color } = badgeText(s);
  const lw = textWidth(label) + 14;
  const rw = textWidth(text) + 14;
  const w = lw + rw;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="20" role="img" aria-label="${esc(label)}: ${esc(text)}">
<title>${esc(label)}: ${esc(text)}</title>
<rect width="${lw}" height="20" rx="3" fill="${COLORS.label}"/>
<rect x="${lw}" width="${rw}" height="20" rx="3" fill="${color}"/>
<rect x="${lw}" width="4" height="20" fill="${color}"/>
<g fill="#fff" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans TC',sans-serif" font-size="11">
<text x="${lw / 2}" y="14" text-anchor="middle">${esc(label)}</text>
<text x="${lw + rw / 2}" y="14" text-anchor="middle">${esc(text)}</text>
</g></svg>`;
}
