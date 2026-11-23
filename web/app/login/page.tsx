"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { copy } from "@/lib/copy";
import { createClient } from "@/lib/supabase/client";

function LoginInner() {
  const params = useSearchParams();
  const [busy, setBusy] = useState(false);
  async function login() {
    setBusy(true);
    const next = params.get("next") ?? "/dashboard";
    await createClient().auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: `${location.origin}/auth/callback?next=${encodeURIComponent(next)}` },
    });
  }
  return (
    <section className="mx-auto flex max-w-md flex-col gap-4 rounded-card border border-border bg-surface p-8 text-center">
      <h1 className="text-2xl font-bold">{copy.login.title}</h1>
      <p className="text-muted">{copy.login.sub}</p>
      {params.get("error") && <p role="alert" className="text-sm text-critical">{copy.login.error}</p>}
      <button type="button" onClick={login} disabled={busy}
        className="rounded-md bg-primary px-5 py-3 font-semibold text-bg transition hover:brightness-110 disabled:opacity-60">
        {busy ? "…" : copy.login.button}
      </button>
    </section>
  );
}

export default function Login() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}
