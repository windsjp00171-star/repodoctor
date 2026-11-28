import Link from "next/link";
import { QuickScanForm } from "@/components/QuickScanForm";
import { copy } from "@/lib/copy";
import { createClient } from "@/lib/supabase/server";

const UNINSTALL_URL = "https://github.com/settings/installations";

export default async function Landing({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  return (
    <>
      {params.account_deleted && (
        <p role="status" className="rounded-card border border-healthy/60 bg-surface p-4 text-sm">
          {copy.dashboard.deleted}{" "}
          <a href={UNINSTALL_URL} className="text-primary underline-offset-4 hover:underline">{copy.dashboard.uninstall}</a>
        </p>
      )}
      <header className="flex flex-col gap-5 pt-8">
        <div className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-primary">{copy.brand}</div>
        <h1 className="max-w-3xl text-4xl font-bold leading-tight text-balance">{copy.landing.headline}</h1>
        <p className="max-w-2xl text-lg text-muted">{copy.landing.sub}</p>
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-3">
            <Link href={user ? "/dashboard" : "/login"}
              className="inline-block rounded-md bg-primary px-6 py-3 text-lg font-semibold text-bg transition hover:brightness-110">
              {user ? copy.landing.dashboard : copy.landing.cta}
            </Link>
            <Link href="/demo"
              className="inline-block rounded-md border border-primary px-6 py-3 text-lg font-semibold text-primary transition hover:bg-primary/10">
              {copy.landing.demo}
            </Link>
          </div>
          {!user && <p className="text-sm text-muted">{copy.landing.ctaNote}</p>}
        </div>
        <div className="max-w-2xl"><QuickScanForm /></div>
      </header>
      <section className="flex flex-col gap-4">
        <h2 className="text-2xl font-bold text-balance">{copy.improve.landingTitle}</h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {copy.improve.landingSteps.map((step, i) => (
            <li key={step.title} className="flex flex-col gap-1 rounded-card border border-border bg-surface p-4">
              <span className="font-num text-2xl font-bold text-primary">{i + 1}</span>
              <span className="font-semibold">{step.title}</span>
              <span className="text-sm leading-relaxed text-muted">{step.body}</span>
            </li>
          ))}
        </ol>
      </section>
      <section className="flex flex-col gap-4">
        <h2 className="text-2xl font-bold text-balance">{copy.landing.coverageTitle}</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {copy.landing.coverage.map((c) => (
            <div key={c.title} className="flex flex-col gap-2 rounded-card border border-border bg-surface p-4">
              <h3 className="font-semibold">{c.title}</h3>
              <ul className="flex flex-col gap-1.5 text-sm leading-relaxed text-muted">
                {c.items.map((it) => (
                  <li key={it} className="flex gap-2"><span aria-hidden className="text-primary">·</span>{it}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
      <section className="rounded-card border border-border bg-surface p-6">
        <h2 className="mb-3 text-lg font-bold">{copy.landing.privacyTitle}</h2>
        <ul className="flex flex-col gap-2 text-muted">
          {copy.landing.privacy.map((p) => (
            <li key={p} className="flex gap-2"><span aria-hidden className="text-healthy">✓</span>{p}</li>
          ))}
        </ul>
        <Link href="/security" className="mt-4 inline-block text-sm text-primary underline-offset-4 hover:underline">
          {copy.landing.securityLink}
        </Link>
      </section>
    </>
  );
}
