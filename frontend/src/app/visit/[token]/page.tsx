import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CaseScreen } from "@/features/case/CaseScreen";
import type { CaseView } from "@/lib/case-view";
import { CoreApiError, coreRequest } from "@/lib/server-api";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Your care plan",
  description: "A private, conversation-linked Billo care plan.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
  referrer: "no-referrer",
};

const VALID_TOKEN = /^[A-Za-z0-9_-]{32,96}$/;

export default async function VisitPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!VALID_TOKEN.test(token)) notFound();
  let view: CaseView;
  try {
    view = await coreRequest(`/public/cases/${encodeURIComponent(token)}`) as CaseView;
  } catch (error) {
    if (error instanceof CoreApiError && [404, 410].includes(error.status)) notFound();
    throw error;
  }
  return <CaseScreen view={view} />;
}
