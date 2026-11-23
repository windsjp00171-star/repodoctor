import Link from "next/link";
import { CONTACT_URL } from "@/lib/legal";

type Section = { title: string; body?: string; items?: string[] };

export function LegalPage({ title, lede, sections }: { title: string; lede: string; sections: Section[] }) {
  return (
    <article className="flex max-w-3xl flex-col gap-6">
      <header className="flex flex-col gap-3">
        <Link href="/" className="text-sm text-muted hover:text-text">← 回首頁</Link>
        <h1 className="text-3xl font-bold">{title}</h1>
        <p className="text-muted">{lede}</p>
      </header>
      {sections.map((s) => (
        <section key={s.title} className="flex flex-col gap-2">
          <h2 className="text-lg font-bold">{s.title}</h2>
          {s.body && <p className="leading-relaxed text-muted">{s.body}</p>}
          {s.items && (
            <ul className="flex list-disc flex-col gap-1 pl-5 leading-relaxed text-muted">
              {s.items.map((it) => <li key={it}>{it}</li>)}
            </ul>
          )}
        </section>
      ))}
      <p className="border-t border-border pt-4 text-sm text-muted">
        聯絡方式：<a href={CONTACT_URL} className="text-primary underline-offset-4 hover:underline">{CONTACT_URL}</a>
      </p>
    </article>
  );
}
