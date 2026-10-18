import type { Metadata } from "next";
import ClassicLanding from "@/features/classic/ClassicLanding";

export const metadata: Metadata = { title: "Classic landing" };

export default function Classic() {
  return <ClassicLanding chatApp="ASI:One" showMarquee />;
}
