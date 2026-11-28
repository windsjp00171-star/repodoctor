import Link from "next/link";
import { copy } from "@/lib/copy";
import { SOURCE_URL } from "@/lib/legal";

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
      <section className="rounded-card border border-healthy/50 bg-surface p-6">
        <h2 className="mb-2 text-lg font-bold">{s.verifyTitle}</h2>
        <p className="mb-4 text-sm leading-relaxed text-muted">{s.verifyLede}</p>
        <ul className="flex flex-col gap-2">
          {s.verify.map((v) => (
            <li key={v.path} className="flex gap-2 leading-relaxed">
              <span aria-hidden className="text-healthy">✓</span>
              <span className="flex min-w-0 flex-col">
                <span>{v.promise}</span>
                <a href={`${SOURCE_URL}/blob/main/${v.path}`} target="_blank" rel="noopener"
                  className="break-all font-mono text-xs text-primary underline-offset-4 hover:underline">{v.path} ↗</a>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-card border border-border bg-surface p-6">
        <h2 className="mb-3 text-lg font-bold">{s.retentionTitle}</h2>
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[minmax(0,16rem)_1fr]">
          {s.retention.map(([k, v]) => (
            <div key={k} className="contents"><dt className="font-semibold">{k}</dt><dd className="text-muted">{v}</dd></div>
          ))}
        </dl>
      </section>

      <div className="grid gap-3 md:grid-cols-3">
        <section className="rounded-card border border-border bg-surface p-5">
          <h2 className="mb-2 font-bold">{s.incidentsTitle}</h2>
          <p className="text-sm leading-relaxed text-muted">{s.incidents}</p>
        </section>
        <section className="rounded-card border border-border bg-surface p-5">
          <h2 className="mb-2 font-bold">{s.reviewTitle}</h2>
          <p className="text-sm leading-relaxed text-muted">{s.review}</p>
        </section>
        <section className="rounded-card border border-border bg-surface p-5">
          <h2 className="mb-2 font-bold">{s.reportTitle}</h2>
          <p className="text-sm leading-relaxed text-muted">{s.report}</p>
          <p className="mt-2 flex flex-wrap gap-3 text-sm">
            <a href={`${SOURCE_URL}/blob/main/SECURITY.md`} target="_blank" rel="noopener" className="text-primary underline-offset-4 hover:underline">{s.reportLink} ↗</a>
            <a href={SOURCE_URL} target="_blank" rel="noopener" className="text-primary underline-offset-4 hover:underline">{s.source} ↗</a>
          </p>
        </section>
      </div>

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
