import { NextResponse } from "next/server";
import { coreRequest } from "@/lib/server-api";
import { normalizeCareSearch } from "@/lib/search";

export async function GET(request) {
  const { q, near } = normalizeCareSearch(request.nextUrl.searchParams);

  try {
    const result = await coreRequest(
      `/care/search?q=${encodeURIComponent(q)}&near=${encodeURIComponent(near)}`,
    );
    return NextResponse.json(result);
  } catch {
    return NextResponse.json(
      { error: "Care search is temporarily unavailable." },
      { status: 503 },
    );
  }
}
