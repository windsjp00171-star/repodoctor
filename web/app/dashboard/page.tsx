import { RepoList } from "@/components/RepoList";
import { copy } from "@/lib/copy";
import { createClient } from "@/lib/supabase/server";
import type { Repo } from "@/lib/types";

export const dynamic = "force-dynamic";

const installUrl = () => `https://github.com/apps/${process.env.NEXT_PUBLIC_GITHUB_APP_SLUG}/installations/new`;

export default async function Dashboard() {
  const supabase = await createClient();
  const [{ data: installs }, { data: repoRows }] = await Promise.all([
    supabase.from("installations").select("id, status, account_login, note").order("created_at"),
    supabase.from("repos")
      .select("id, full_name, language, last_scan:scans!repos_last_scan_fk(id, status, score, summary, created_at)")
      .order("full_name"),
  ]);
  const repos = (repoRows ?? []) as unknown as Repo[];
  const pending = (installs ?? []).filter((i) => i.status === "pending");
  const rejected = (installs ?? []).filter((i) => i.status === "rejected");
  const hasActive = (installs ?? []).some((i) => i.status === "active");

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-primary">{copy.brand}</div>
          <h1 className="text-3xl font-bold">{copy.dashboard.title}</h1>
        </div>
        <form action="/auth/logout" method="post">
          <button className="text-sm text-muted hover:text-text">{copy.dashboard.logout}</button>
        </form>
      </header>

      {!hasActive && (
        <section className="flex flex-col gap-3 rounded-card border border-primary/50 bg-surface p-6">
          <h2 className="text-lg font-bold">{copy.dashboard.installTitle}</h2>
          <p className="text-muted">{copy.dashboard.installSub}</p>
          <div><a href={installUrl()} className="inline-block rounded-md bg-primary px-4 py-2 font-semibold text-bg">{copy.dashboard.install}</a></div>
        </section>
      )}
      {pending.length > 0 && <p className="rounded-card border border-border bg-surface p-4 text-sm text-muted">{copy.dashboard.pending}</p>}
      {rejected.map((i) => (
        <p key={i.id} role="alert" className="rounded-card border border-critical/60 bg-surface p-4 text-sm">
          <span className="text-critical">{copy.dashboard.rejected}</span>{i.note}
        </p>
      ))}

      {hasActive && <RepoList repos={repos} aiEnabled={process.env.NEXT_PUBLIC_AI_ENABLED === "true"} />}
      {hasActive && repos.length === 0 && <p className="text-muted">{copy.dashboard.noRepos}</p>}
      {hasActive && <a href={installUrl()} className="text-sm text-primary">{copy.dashboard.manage} →</a>}
    </>
  );
}
