import { LegalPage } from "@/components/LegalPage";
import { terms } from "@/lib/legal";

export const metadata = { title: "使用條款 — RepoDoctor" };

export default function Terms() {
  return <LegalPage {...terms} />;
}
