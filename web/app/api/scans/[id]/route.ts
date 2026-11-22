import { NextResponse } from "next/server";
import { copy } from "@/lib/copy";
import { getScan } from "@/lib/scans";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let scan = null;
  try {
    scan = getScan(id);
  } catch {
    scan = null;
  }
  if (!scan) return NextResponse.json({ success: false, error: copy.errors.notFound }, { status: 404 });
  return NextResponse.json({ success: true, scan });
}
