import type { Metadata } from "next";
import { notFound } from "next/navigation";

import JourneyScreen, { JOURNEY_STAGES, type JourneyStage } from "@/features/journey/JourneyScreen";

export const metadata: Metadata = {
  title: "Care journey",
  description: "Follow a Billo case before, during, and after care.",
};

export function generateStaticParams() {
  return JOURNEY_STAGES.map((stage) => ({ stage }));
}

export default async function JourneyStagePage({ params }: { params: Promise<{ stage: string }> }) {
  const { stage } = await params;
  if (!(JOURNEY_STAGES as readonly string[]).includes(stage)) notFound();
  return <JourneyScreen stage={stage as JourneyStage} />;
}
