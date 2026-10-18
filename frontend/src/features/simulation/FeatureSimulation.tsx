"use client";

import { useState } from "react";
import { BilloWord } from "@/components/BilloWord";
import { QRCells } from "@/components/QRCells";
import { formatMoney, normalizePlaces } from "@/lib/format";
import { makeQR } from "@/lib/qr";
import styles from "./FeatureSimulation.module.css";

export type FeatureStep = "safety" | "prices" | "estimate" | "visit" | "scan" | "match" | "payment" | "benefits";

const COPY = {
  safety: ["SAFETY SCREEN", "Start with urgent warning signs", "RUN DEMO SCREEN", "Demo screen complete", "mint"],
  prices: ["CARE SEARCH", "Compare demo care options", "RUN DEMO SEARCH", "3 demo options shown", "gold"],
  estimate: ["PRICE ESTIMATE", "Review a sample cost range", "BUILD DEMO ESTIMATE", "Demo estimate saved", "peach"],
  visit: ["VISIT LOG", "Track services and estimates", "LOG DEMO SERVICE", "Demo service added", "lilac"],
  scan: ["DOCUMENT READER", "Preview bill extraction", "RUN DEMO SCAN", "3 sample lines shown", "blue"],
  match: ["BILL REVIEW", "Compare extracted charges", "RUN DEMO REVIEW", "Demo charges organized", "ink"],
  payment: ["PAYMENT SAFEGUARDS", "Review the clinic and amount", "RUN DEMO CHECK", "Ready for your review", "mint"],
  benefits: ["BENEFIT PATHS", "Explore possible next steps", "RUN DEMO CHECK", "2 possible paths shown", "gold"],
} satisfies Record<FeatureStep, readonly [string, string, string, string, string]>;

type Provider = { name: string; kind: string; address: string; hours: string; low: number; typical: number; source: string };
const PROVIDERS: Provider[] = [
  { name: "Westwood Urgent Care", kind: "urgent care", address: "10900 Wilshire Blvd, Los Angeles", hours: "sample hours", low: 180, typical: 240, source: "synthetic demo data" },
  { name: "Campus Health Clinic", kind: "clinic", address: "221 Charles E Young Dr S, Los Angeles", hours: "sample hours", low: 120, typical: 180, source: "synthetic demo data" },
  { name: "Santa Monica Emergency Room", kind: "ER", address: "1250 16th St, Santa Monica", hours: "sample hours", low: 1200, typical: 1800, source: "synthetic demo data" },
];
const PAYMENT_QR = makeQR("BILLO-DEMO-PAY-8F2A");

const STEPS: ReadonlyArray<readonly [FeatureStep, string]> = [
  ["safety", "Safety"], ["prices", "Prices"], ["estimate", "Estimate"], ["visit", "Visit log"],
  ["scan", "Bill scan"], ["match", "Match"], ["payment", "Payment"], ["benefits", "Benefits"],
];

function Results({ step, complete, providers }: { step: FeatureStep; complete: boolean; providers: Provider[] }) {
  if (step === "prices") return <div className={styles.providerList}>{providers.map((provider, index) => <div className={styles.provider} key={provider.name}><span className={styles.number}>{String(index + 1).padStart(2, "0")}</span><div><h3>{provider.name}</h3><span className={styles.tag}>{provider.kind.toUpperCase()}</span><p>{provider.address} · {provider.hours}</p><small>{provider.source}</small></div><div className={styles.price}><small>TYPICAL</small><strong>{formatMoney(provider.typical)}</strong><span>from {formatMoney(provider.low)}</span></div></div>)}</div>;

  const rows: Record<Exclude<FeatureStep, "prices">, string[][]> = {
    safety: [["Chest pain", "Not selected"], ["Trouble breathing", "Not selected"], ["Sudden weakness", "Not selected"], ["Next step", complete ? "Demo care guidance" : "Run the demo"]],
    estimate: [["Sample office visit", "$240"], ["Sample knee X-ray", "$120"], ["Demo estimate", complete ? "$360" : "$240–$480"]],
    visit: [["Sample office visit", "$240"], ["Sample knee X-ray", complete ? "$120" : "Not logged"], ["Running demo estimate", complete ? "$360" : "$240"]],
    scan: [["99203 · Sample office visit", "$240"], ["73560 · Sample knee X-ray", "$120"], ["Printed demo total", complete ? "$360" : "Run the demo"]],
    match: [["Provider and NPI", "Demo match"], ["Office visit", "$240 · printed"], ["Knee X-ray", complete ? "$120 · printed" : "$120 · review"]],
    payment: [["Sample clinic", "Westwood Urgent Care"], ["Amount to review", "$360"], ["Approval status", complete ? "Not approved" : "Run the demo"]],
    benefits: [["HSA path", complete ? "Possible · verify" : "Run the demo"], ["Out-of-network claim", "Possible · verify"], ["Decision maker", "Plan administrator"]],
  };
  return <div className={styles.resultCard}>{rows[step].map(([label, value], index) => <div className={styles.resultRow} key={label}><span className={index < rows[step].length - 1 ? styles.check : styles.count}>{index < rows[step].length - 1 ? "i" : complete ? "→" : "…"}</span><div><strong>{label}</strong><small>{index < rows[step].length - 1 ? "Synthetic demo data" : "Independent review required"}</small></div><b>{value}</b></div>)}</div>;
}

export function FeatureSimulation({ step, onStepChange }: { step: FeatureStep; onStepChange: (step: FeatureStep) => void }) {
  const [complete, setComplete] = useState(false);
  const [running, setRunning] = useState(false);
  const [query, setQuery] = useState("knee pain after a fall");
  const [near, setNear] = useState("UCLA");
  const [visitNote, setVisitNote] = useState("Knee X-ray");
  const [providers, setProviders] = useState<Provider[]>(PROVIDERS);
  const [eyebrow, title, action, done, accent] = COPY[step];

  const selectStep = (nextStep: FeatureStep) => {
    setComplete(false);
    onStepChange(nextStep);
  };

  const runSimulation = async () => {
    setRunning(true);
    if (step === "prices") {
      try {
        const response = await fetch(`/api/care/search?q=${encodeURIComponent(query)}&near=${encodeURIComponent(near)}`);
        const places = normalizePlaces(await response.json());
        if (places.length) setProviders(places);
      } catch {
        setProviders(PROVIDERS);
      }
    }
    window.setTimeout(() => { setComplete(true); setRunning(false); }, 500);
  };

  return <div className={styles.embed} aria-label="Interactive Billo workflow simulation">
    <div className={styles.window} data-accent={accent}>
      <div className={styles.chrome}><span className={styles.dots}>● ● ●</span><strong>Case 8F2A · interactive demo</strong></div>
      <nav className={styles.stepbar} aria-label="Simulation steps">{STEPS.map(([id, label]) => <button type="button" key={id} aria-pressed={step === id} onClick={() => selectStep(id)}>{label}</button>)}</nav>
      <div className={styles.layout}>
        <aside><strong><BilloWord /></strong><button className={styles.selected}>Overview</button><button>Inputs</button><button>Results</button><span>Interactive demo</span></aside>
        <main>
          <div className={styles.heading}><div><p>{eyebrow}</p><h2 id="simulation-title">{title}</h2></div><span className={styles.status}>{complete ? "COMPLETE" : "DEMO"}</span></div>
          {step === "prices" && <div className={styles.search}><label>WHAT HAPPENED?<input value={query} onChange={(event) => setQuery(event.target.value)} /></label><label>NEAR<input value={near} onChange={(event) => setNear(event.target.value)} /></label><button type="button" onClick={runSimulation} disabled={running}>{running ? "SEARCHING…" : action}</button></div>}
          {step === "safety" && <div className={styles.inputPanel}><label>WHAT HAPPENED?<textarea value={query} onChange={(event) => setQuery(event.target.value)} /></label><div className={styles.checkboxes}><label><input type="checkbox" /> Chest pain</label><label><input type="checkbox" /> Trouble breathing</label><label><input type="checkbox" /> Sudden weakness</label></div></div>}
          {step === "estimate" && <div className={styles.inputPanel}><label>PLACE<select defaultValue="westwood"><option value="westwood">Westwood Urgent Care</option><option value="campus">Campus Health Clinic</option></select></label><label>LIKELY SERVICE<select defaultValue="visit"><option value="visit">Office visit</option><option value="xray">Office visit + X-ray</option></select></label></div>}
          {step === "visit" && <div className={styles.inputPanel}><label>SERVICE RECEIVED<input value={visitNote} onChange={(event) => setVisitNote(event.target.value)} /></label><label>QUOTED AMOUNT<input inputMode="decimal" defaultValue="120" /></label></div>}
          {step === "scan" && <div className={styles.upload}><span>DEMO RECEIPT OR BILL</span><strong>Select a local file</strong><small>This preview does not upload or read it; the result below uses sample data.</small><input type="file" accept="image/*,.pdf" aria-label="Choose a local demo bill" /></div>}
          {step === "match" && <div className={styles.inputPanel}><label><input type="checkbox" defaultChecked /> Match provider and NPI</label><label><input type="checkbox" defaultChecked /> Compare bill with visit log</label><label><input type="checkbox" /> Flag unexplained charges</label></div>}
          {step === "benefits" && <div className={styles.inputPanel}><label>HOW DID YOU PAY?<select defaultValue="card"><option value="card">Personal card</option><option value="hsa">HSA / FSA card</option></select></label><label>INSURANCE<select defaultValue="ppo"><option value="ppo">PPO plan</option><option value="none">No insurance</option><option value="school">School plan</option></select></label></div>}
          {step !== "prices" && <div className={styles.caseTotal}><div><small>CURRENT CASE</small><span>{complete ? done : "Ready to simulate"}</span></div><strong>{["payment", "estimate", "visit", "match"].includes(step) ? "$360" : step === "benefits" ? "$480" : "BILLO"}</strong></div>}
          {step === "payment" && <div className={styles.paymentQr}><div><span>DEMO CLINIC PAYMENT QR</span><strong>Westwood Urgent Care</strong><small>Static preview only. No payment can be approved or sent from this screen.</small></div><div className={styles.qr}><QRCells cells={PAYMENT_QR} /></div></div>}
          <Results step={step} complete={complete} providers={providers} />
          <div className={styles.actions}><button type="button" className={styles.secondary} onClick={() => setComplete(false)}>RESET</button><button type="button" className={styles.primary} onClick={runSimulation} disabled={running}>{running ? "WORKING…" : complete ? "RUN AGAIN" : action}</button></div>
          <p className={styles.disclaimer}>Synthetic demo data only · not a quote, diagnosis, coverage decision, private case record, or payment.</p>
        </main>
      </div>
    </div>
  </div>;
}
