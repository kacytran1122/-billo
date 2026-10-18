import { NextResponse } from "next/server";
import { coreRequest } from "@/lib/server-api";

export async function GET(request) {
  const search = request.nextUrl.searchParams;
  const q = search.get("q")?.slice(0, 160) || "routine visit";
  const near = search.get("near")?.slice(0, 80) || "UCLA";

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
