import type { Metadata } from "next";
import { notFound } from "next/navigation";
import FeatureWorkspace from "@/features/simulation/FeatureWorkspace";
import type { FeatureStep } from "@/features/simulation/FeatureSimulation";

const STEPS: FeatureStep[] = ["safety", "prices", "estimate", "visit", "scan", "match", "payment", "benefits"];
export const metadata: Metadata = { title: "Billo feature screen", description: "Explore a specific Billo feature using an interactive demo. Not a private case record." };
export function generateStaticParams() { return STEPS.map(step => ({ step })); }
export default async function ToolPage({ params }: { params: Promise<{ step: string }> }) {
  const { step } = await params;
  if (!STEPS.includes(step as FeatureStep)) notFound();
  return <FeatureWorkspace initialStep={step as FeatureStep} />;
}
