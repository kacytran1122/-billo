"use client";

import Link from "next/link";
import { useState } from "react";
import { FeatureSimulation, type FeatureStep } from "./FeatureSimulation";

export default function FeatureWorkspace({ initialStep }: { initialStep: FeatureStep }) {
  const [step, setStep] = useState(initialStep);
  return (
    <div style={{ minHeight: "100vh", padding: "24px clamp(12px, 4vw, 56px)", background: "#f5f3ee", color: "#201f1d" }}>
      <header style={{ maxWidth: 1200, margin: "0 auto 24px" }}>
        <Link href="/" style={{ color: "inherit", fontSize: 22 }}>billo</Link>
        <h1 style={{ fontSize: "clamp(24px, 4vw, 40px)", marginBottom: 12 }}>Your next step, explained.</h1>
        <p style={{ maxWidth: 760, lineHeight: 1.6 }}>Interactive feature preview with demo data. This is not your private case record. Continue in your Billo iMessage conversation to submit a document or update your case. Do not upload sensitive documents into this demo.</p>
      </header>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}><FeatureSimulation step={step} onStepChange={setStep} /></div>
    </div>
  );
}
