import type { Metadata } from "next";
import PrototypePage from "@/features/prototype/PrototypePage";

export const metadata: Metadata = { title: "Prototype" };

export default function Prototype() {
  return <PrototypePage startScreen="landing" />;
}
