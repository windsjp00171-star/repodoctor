import { QuickScanView } from "@/components/QuickScanView";

export const metadata = { title: "秒檢結果 — RepoDoctor" };

export default async function Quick({ params }: { params: Promise<{ id: string }> }) {
  return <QuickScanView id={(await params).id} />;
}
