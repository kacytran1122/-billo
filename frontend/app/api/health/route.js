import { NextResponse } from "next/server";
import { coreRequest } from "@/lib/server-api";

export async function GET() {
  try {
    return NextResponse.json(await coreRequest("/health"));
  } catch {
    return NextResponse.json({ ok: false }, { status: 503 });
  }
}
