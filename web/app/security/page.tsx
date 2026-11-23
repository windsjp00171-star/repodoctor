import Link from "next/link";
import { copy } from "@/lib/copy";

export const metadata = { title: "隱私與安全 — RepoDoctor" };

export default function Security() {
  const s = copy.security;
  return (
    <>
      <header className="flex flex-col gap-3">
        <Link href="/" className="text-sm text-muted hover:text-text">{s.back}</Link>
        <h1 className="text-3xl font-bold">{s.title}</h1>
        <p className="max-w-2xl text-muted">{s.lede}</p>
      </header>
      {s.sections.map((sec) => (
        <section key={sec.title} className="rounded-card border border-border bg-surface p-6">
          <h2 className="mb-3 text-lg font-bold">{sec.title}</h2>
          <ul className="flex flex-col gap-2">
            {sec.items.map((it) => (
              <li key={it} className="flex gap-2 leading-relaxed">
                <span aria-hidden className="text-healthy">✓</span>
                <span>{it}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
      <section className="rounded-card border border-high/50 bg-surface p-6">
        <h2 className="mb-3 text-lg font-bold">{s.limitsTitle}</h2>
        <ul className="flex flex-col gap-2 text-muted">
          {s.limits.map((it) => (
            <li key={it} className="flex gap-2 leading-relaxed">
              <span aria-hidden className="text-high">!</span>
              <span>{it}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
