import { NextResponse } from "next/server";
import { coreRequest } from "@/lib/server-api";
import { normalizeCareSearch } from "@/lib/search";

export async function GET(request: Request) {
  const { q, near } = normalizeCareSearch(new URL(request.url).searchParams);
  try {
    return NextResponse.json(await coreRequest(`/care/search?q=${encodeURIComponent(q)}&near=${encodeURIComponent(near)}`));
  } catch {
    return NextResponse.json({ error: "Care search is temporarily unavailable." }, { status: 503 });
  }
}
