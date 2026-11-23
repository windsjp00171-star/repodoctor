import Link from "next/link";
import { AutoRefresh } from "@/components/AutoRefresh";
import { DeleteMyData } from "@/components/DeleteMyData";
import { InstallGuide } from "@/components/InstallGuide";
import { RepoList } from "@/components/RepoList";
import { copy } from "@/lib/copy";
import { createClient } from "@/lib/supabase/server";
import type { Repo } from "@/lib/types";

export const dynamic = "force-dynamic";

const SLUG = process.env.NEXT_PUBLIC_GITHUB_APP_SLUG;
const UNINSTALL_URL = "https://github.com/settings/installations";

/** 帶上使用者的 GitHub 帳號 id，GitHub 會跳過「要裝在哪個帳號」那一頁，直接選 repo。 */
function installUrl(githubId: string | null) {
  return githubId && /^\d+$/.test(githubId)
    ? `https://github.com/apps/${SLUG}/installations/new/permissions?target_id=${githubId}`
    : `https://github.com/apps/${SLUG}/installations/new`;
}

export default async function Dashboard({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const gh = user?.identities?.find((i) => i.provider === "github");
  const githubId = (gh?.identity_data?.provider_id as string | undefined) ?? gh?.id ?? null;

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
  const d = copy.dashboard;

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-primary">{copy.brand}</div>
          <h1 className="text-3xl font-bold">{d.title}</h1>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/security" className="text-muted hover:text-text">{d.security}</Link>
          <form action="/auth/logout" method="post">
            <button className="text-muted hover:text-text">{d.logout}</button>
          </form>
        </div>
      </header>

      {params.deleted && (
        <p role="status" className="rounded-card border border-healthy/60 bg-surface p-4 text-sm">
          {d.deleted}{" "}
          <a href={UNINSTALL_URL} className="text-primary underline-offset-4 hover:underline">{d.uninstall}</a>
        </p>
      )}
      {params.delete_error && (
        <p role="alert" className="rounded-card border border-critical/60 bg-surface p-4 text-sm text-critical">{copy.errors.deleteFailed}</p>
      )}

      {!hasActive && pending.length === 0 && <InstallGuide installUrl={installUrl(githubId)} />}
      {pending.length > 0 && (
        <p className="flex items-center gap-3 rounded-card border border-primary/50 bg-surface p-4 text-sm">
          <span aria-hidden className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
          {d.pending}
          <AutoRefresh />
        </p>
      )}
      {rejected.map((i) => (
        <p key={i.id} role="alert" className="rounded-card border border-critical/60 bg-surface p-4 text-sm">
          <span className="text-critical">{d.rejected}</span>{i.note}
        </p>
      ))}

      {hasActive && <RepoList repos={repos} aiEnabled={process.env.NEXT_PUBLIC_AI_ENABLED === "true"} />}
      {hasActive && repos.length === 0 && <p className="text-muted">{d.noRepos}</p>}
      {hasActive && <a href={installUrl(githubId)} className="text-sm text-primary">{d.manage} →</a>}

      {(installs ?? []).length > 0 && <DeleteMyData />}
    </>
  );
}
