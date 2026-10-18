import type { Metadata } from "next";
import BrandBoard from "@/features/brand/BrandBoard";

export const metadata: Metadata = { title: "Logo explorations" };

export default function Brand() {
  return <BrandBoard />;
}
