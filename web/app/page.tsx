import Link from "next/link";
import { copy } from "@/lib/copy";
import { createClient } from "@/lib/supabase/server";

export default async function Landing() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  return (
    <>
      <header className="flex flex-col gap-5 pt-8">
        <div className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-primary">{copy.brand}</div>
        <h1 className="max-w-3xl text-4xl font-bold leading-tight text-balance">{copy.landing.headline}</h1>
        <p className="max-w-2xl text-lg text-muted">{copy.landing.sub}</p>
        <div className="flex flex-col gap-2">
          <div>
            <Link href={user ? "/dashboard" : "/login"}
              className="inline-block rounded-md bg-primary px-6 py-3 text-lg font-semibold text-bg transition hover:brightness-110">
              {user ? copy.landing.dashboard : copy.landing.cta}
            </Link>
          </div>
          {!user && <p className="text-sm text-muted">{copy.landing.ctaNote}</p>}
        </div>
      </header>
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
