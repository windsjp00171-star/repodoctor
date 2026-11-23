import { LegalPage } from "@/components/LegalPage";
import { privacy } from "@/lib/legal";

export const metadata = { title: "隱私權政策 — RepoDoctor" };

export default function Privacy() {
  return <LegalPage {...privacy} />;
}
