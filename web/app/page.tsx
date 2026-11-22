import { ProjectList } from "@/components/ProjectList";
import { copy } from "@/lib/copy";
import { aiAvailable, listProjects, listScans } from "@/lib/scans";

export const dynamic = "force-dynamic";

export default function Home() {
  const scans = listScans();
  const projects = listProjects().map((p) => ({ ...p, last: scans.find((s) => s.path === p.path) ?? null }));
  return (
    <>
      <header className="flex flex-col gap-3">
        <div className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-primary">{copy.brand}</div>
        <h1 className="text-3xl font-bold text-balance">{copy.tagline}</h1>
        <p className="max-w-2xl text-muted">{copy.intro}</p>
      </header>
      <ProjectList projects={projects} aiAvailable={aiAvailable()} />
    </>
  );
}
