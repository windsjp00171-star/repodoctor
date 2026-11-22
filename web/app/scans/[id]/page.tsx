import { notFound } from "next/navigation";
import { ScanView } from "@/components/ScanView";
import { getScan } from "@/lib/scans";

export const dynamic = "force-dynamic";

export default async function ScanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let scan = null;
  try {
    scan = getScan(id);
  } catch {
    scan = null;
  }
  if (!scan) notFound();
  return <ScanView initial={scan} />;
}
