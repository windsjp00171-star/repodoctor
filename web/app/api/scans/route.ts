import { NextResponse } from "next/server";
import { copy } from "@/lib/copy";
import { listScans, startScan } from "@/lib/scans";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({ success: true, scans: listScans() });
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  if (typeof body.path !== "string" || !body.path.trim()) {
    return NextResponse.json({ success: false, error: copy.errors.badPath }, { status: 400 });
  }
  try {
    const id = startScan(body.path.trim(), Boolean(body.ai));
    return NextResponse.json({ success: true, id }, { status: 201 });
  } catch {
    return NextResponse.json({ success: false, error: copy.errors.badPath }, { status: 400 });
  }
}
