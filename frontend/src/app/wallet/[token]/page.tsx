import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { WalletScreen } from "@/features/case/WalletScreen";
import type { WalletView } from "@/lib/case-view";
import { CoreApiError, coreRequest } from "@/lib/server-api";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Wallet handoff",
  description: "Review a payment handoff prepared in your Billo conversation.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
  referrer: "no-referrer",
};

const VALID_TOKEN = /^[A-Za-z0-9_-]{32,96}$/;

export default async function WalletPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!VALID_TOKEN.test(token)) notFound();
  let view: WalletView;
  try {
    view = await coreRequest(`/public/wallet/${encodeURIComponent(token)}`) as WalletView;
  } catch (error) {
    if (error instanceof CoreApiError && [404, 410].includes(error.status)) notFound();
    throw error;
  }
  return <WalletScreen view={view} />;
}
