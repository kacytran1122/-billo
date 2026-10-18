import { NextResponse } from "next/server";

import { CoreApiError, coreRequest } from "@/lib/server-api";

const VALID_CODE = /^BILLO-[A-Z2-9]{4}-[A-Z2-9]{4}$/;
const PRIVATE_HEADERS = { "Cache-Control": "private, no-store, max-age=0", "Referrer-Policy": "no-referrer" };

export async function GET(_request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!VALID_CODE.test(token)) return NextResponse.json({ status: "unknown" }, { status: 404, headers: PRIVATE_HEADERS });
  try {
    const result = await coreRequest(`/api/link/${encodeURIComponent(token)}`);
    return NextResponse.json(result, { headers: PRIVATE_HEADERS });
  } catch (error) {
    const status = error instanceof CoreApiError && [404, 410].includes(error.status) ? error.status : 503;
    return NextResponse.json({ status: status === 410 ? "expired" : "unknown" }, { status, headers: PRIVATE_HEADERS });
  }
}
