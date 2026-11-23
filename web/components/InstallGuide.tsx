import Link from "next/link";
import { copy } from "@/lib/copy";

/** 去 GitHub 之前先說清楚：到了那邊會看到什麼、按哪裡。 */
export function InstallGuide({ installUrl }: { installUrl: string }) {
  const d = copy.dashboard;
  return (
    <section className="flex flex-col gap-5 rounded-card border border-primary/50 bg-surface p-6">
      <div>
        <h2 className="text-xl font-bold">{d.installTitle}</h2>
        <p className="mt-1 text-muted">{d.installSub}</p>
      </div>
      <ol className="grid gap-3 sm:grid-cols-3">
        {d.installSteps.map((step, i) => (
          <li key={step.title} className="flex flex-col gap-1 rounded-card border border-border bg-bg p-4">
            <span className="font-num text-2xl font-bold text-primary">{i + 1}</span>
            <span className="font-semibold">{step.title}</span>
            <span className="text-sm text-muted">{step.body}</span>
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-4">
        <a href={installUrl} className="rounded-md bg-primary px-5 py-3 font-semibold text-bg transition hover:brightness-110">
          {d.install} →
        </a>
        <Link href="/security" className="text-sm text-muted underline-offset-4 hover:text-text hover:underline">
          {d.installSecurity}
        </Link>
      </div>
    </section>
  );
}
