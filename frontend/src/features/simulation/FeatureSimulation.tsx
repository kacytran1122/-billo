"use client";

import { useState } from "react";
import { BilloWord } from "@/components/BilloWord";
import styles from "./FeatureSimulation.module.css";

export type FeatureStep = "safety" | "prices" | "estimate" | "visit" | "scan" | "match" | "payment" | "benefits";

const COPY = {
  safety: ["SAFETY CHECK", "Tell Billo what happened", "CHECK SYMPTOMS", "No emergency signs found", "mint"],
  prices: ["CARE SEARCH", "Compare care near you", "COMPARE CARE", "3 options compared", "gold"],
  estimate: ["PRICE ESTIMATE", "Know the likely cost", "BUILD ESTIMATE", "Estimate saved", "peach"],
  visit: ["LIVE VISIT LOG", "Keep a running total", "LOG SERVICE", "Service added", "lilac"],
  scan: ["DOCUMENT READER", "Turn the bill into data", "SCAN BILL", "3 lines extracted", "blue"],
  match: ["BILL AUDIT", "Match every charge", "VERIFY CHARGES", "All charges explained", "ink"],
  payment: ["PAYMENT GUARD", "Approve only the right amount", "VERIFY PAYMENT", "Payment is ready", "mint"],
  benefits: ["BENEFIT FINDER", "Find money you may get back", "CHECK BENEFITS", "2 possible paths found", "gold"],
} satisfies Record<FeatureStep, readonly [string, string, string, string, string]>;

const PROVIDERS = [
  ["01", "Westwood Urgent Care", "URGENT CARE", "$240", "from $180"],
  ["02", "Campus Health Clinic", "CLINIC", "$180", "from $120"],
  ["03", "Santa Monica Emergency Room", "ER", "$1,800", "from $1,200"],
];

const STEPS: ReadonlyArray<readonly [FeatureStep, string]> = [
  ["safety", "Safety"], ["prices", "Prices"], ["estimate", "Estimate"], ["visit", "Visit log"],
  ["scan", "Bill scan"], ["match", "Match"], ["payment", "Payment"], ["benefits", "Benefits"],
];

function Results({ step, complete }: { step: FeatureStep; complete: boolean }) {
  if (step === "prices") return <div className={styles.providerList}>{PROVIDERS.map((provider) => <div className={styles.provider} key={provider[0]}><span className={styles.number}>{provider[0]}</span><div><h3>{provider[1]}</h3><span className={styles.tag}>{provider[2]}</span><p>Los Angeles · open today · public price data</p></div><div className={styles.price}><small>TYPICAL</small><strong>{provider[3]}</strong><span>{provider[4]}</span></div></div>)}</div>;

  const rows: Record<Exclude<FeatureStep, "prices">, string[][]> = {
    safety: [["Chest pain", "No"], ["Trouble breathing", "No"], ["Sudden weakness", "No"], ["Recommended next step", complete ? "Urgent care" : "Waiting"]],
    estimate: [["Office visit", "$240"], ["Knee X-ray", "$120"], ["Expected total", complete ? "$360" : "$240–$480"]],
    visit: [["Office visit", "$240"], ["Knee X-ray", complete ? "$120" : "Not logged"], ["Running estimate", complete ? "$360" : "$240"]],
    scan: [["99203 · Office visit", "$240"], ["73560 · Knee X-ray", "$120"], ["Document total", complete ? "$360" : "Scanning…"]],
    match: [["Provider and NPI", "Matched"], ["Office visit", "$240 · verified"], ["Knee X-ray", complete ? "$120 · verified" : "$120 · review"]],
    payment: [["Clinic", "Westwood Urgent Care"], ["Approved amount", "$360"], ["Payment status", complete ? "Ready for approval" : "Checking"]],
    benefits: [["HSA reimbursement", complete ? "$360 · possible" : "Checking"], ["Out-of-network claim", "$120 · possible"], ["Next step", "Review eligibility"]],
  };
  return <div className={styles.resultCard}>{rows[step].map(([label, value], index) => <div className={styles.resultRow} key={label}><span className={index < rows[step].length - 1 ? styles.check : styles.count}>{index < rows[step].length - 1 ? "✓" : complete ? "2" : "…"}</span><div><strong>{label}</strong><small>{index < rows[step].length - 1 ? "Billo checked the record" : "Personal review required"}</small></div><b>{value}</b></div>)}</div>;
}

export function FeatureSimulation({ step, onStepChange }: { step: FeatureStep; onStepChange: (step: FeatureStep) => void }) {
  const [complete, setComplete] = useState(false);
  const [eyebrow, title, action, done, accent] = COPY[step];

  const selectStep = (nextStep: FeatureStep) => {
    setComplete(false);
    onStepChange(nextStep);
  };

  return <div className={styles.embed} aria-label="Interactive Billo workflow simulation">
    <div className={styles.window} data-accent={accent}>
      <div className={styles.chrome}><span className={styles.dots}>● ● ●</span><strong>Case 8F2A · interactive demo</strong></div>
      <nav className={styles.stepbar} aria-label="Simulation steps">{STEPS.map(([id, label]) => <button type="button" key={id} aria-pressed={step === id} onClick={() => selectStep(id)}>{label}</button>)}</nav>
      <div className={styles.layout}>
        <aside><strong><BilloWord /></strong><button className={styles.selected}>Overview</button><button>Inputs</button><button>Results</button><span>Interactive demo</span></aside>
        <main>
          <div className={styles.heading}><div><p>{eyebrow}</p><h2 id="simulation-title">{title}</h2></div><span className={styles.status}>{complete ? "COMPLETE" : "DEMO"}</span></div>
          {step === "prices" && <div className={styles.search}><label>WHAT HAPPENED?<input defaultValue="knee pain after a fall" /></label><label>NEAR<input defaultValue="UCLA" /></label><button type="button" onClick={() => setComplete(true)}>{action}</button></div>}
          {step !== "prices" && <div className={styles.caseTotal}><div><small>CURRENT CASE</small><span>{complete ? done : "Ready to simulate"}</span></div><strong>{["payment", "estimate", "visit", "match"].includes(step) ? "$360" : step === "benefits" ? "$480" : "BILLO"}</strong></div>}
          <Results step={step} complete={complete} />
          <div className={styles.actions}><button type="button" className={styles.secondary} onClick={() => setComplete(false)}>RESET</button><button type="button" className={styles.primary} onClick={() => setComplete(true)}>{complete ? "SIMULATION COMPLETE ✓" : action}</button></div>
          <p className={styles.disclaimer}>Demo data only · Billo does not provide medical or insurance advice.</p>
        </main>
      </div>
    </div>
  </div>;
}
