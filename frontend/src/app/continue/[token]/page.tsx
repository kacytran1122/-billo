import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { HandoffScreen } from "@/features/case/HandoffScreen";
import type { HandoffView } from "@/lib/case-view";
import { CoreApiError, coreRequest } from "@/lib/server-api";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Continue with Billo",
  description: "Securely continue a Billo conversation in WhatsApp.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
  referrer: "no-referrer",
};

const VALID_CODE = /^BILLO-[A-Z2-9]{4}-[A-Z2-9]{4}$/;

export default async function ContinuePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!VALID_CODE.test(token)) notFound();
  let initial: HandoffView;
  try {
    initial = await coreRequest(`/api/link/${encodeURIComponent(token)}`) as HandoffView;
  } catch (error) {
    if (error instanceof CoreApiError && [404, 410].includes(error.status)) notFound();
    throw error;
  }
  return <HandoffScreen token={token} initial={initial} />;
}
