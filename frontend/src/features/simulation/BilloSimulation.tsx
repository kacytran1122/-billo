"use client";

import { useState, type FormEvent } from "react";

import { formatMoney, normalizePlaces } from "@/lib/format";
import styles from "./BilloSimulation.module.css";

type Mode = "search" | "case";
type CaseTab = "overview" | "visit" | "documents" | "benefits";

const DEMO_PLACES = [
  { name: "Westwood Urgent Care", kind: "urgent_care", address: "10900 Wilshire Blvd, Los Angeles", hours: "Open until 9 pm", low: 180, typical: 240, source: "synthetic demo" },
  { name: "Campus Health Clinic", kind: "clinic", address: "221 Charles E Young Dr S, Los Angeles", hours: "Open until 6 pm", low: 120, typical: 180, source: "synthetic demo" },
  { name: "Santa Monica Emergency Room", kind: "ER", address: "1250 16th St, Santa Monica", hours: "Open 24 hours", low: 1200, typical: 1800, source: "synthetic demo" },
];

export function BilloSimulation() {
  const [mode, setMode] = useState<Mode>("search");
  const [caseTab, setCaseTab] = useState<CaseTab>("overview");
  const [query, setQuery] = useState("knee pain after a fall");
  const [near, setNear] = useState("UCLA");
  const [places, setPlaces] = useState(DEMO_PLACES);
  const [loading, setLoading] = useState(false);

  async function compareCare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    try {
      const [response] = await Promise.all([
        fetch(`/api/care/search?q=${encodeURIComponent(query)}&near=${encodeURIComponent(near)}`),
        new Promise((resolve) => window.setTimeout(resolve, 420)),
      ]);
      if (!response.ok) throw new Error("search unavailable");
      const normalized = normalizePlaces(await response.json());
      setPlaces(normalized.length ? normalized : DEMO_PLACES);
    } catch {
      setPlaces(DEMO_PLACES);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.simulation}>
      <div className={styles.modeSwitch} aria-label="Choose a Billo simulation">
        <button type="button" aria-pressed={mode === "search"} onClick={() => setMode("search")}>Compare care</button>
        <button type="button" aria-pressed={mode === "case"} onClick={() => setMode("case")}>Review a case</button>
      </div>

      <div className={styles.window}>
        <div className={styles.windowBar}>
          <span /><span /><span />
          <strong>{mode === "search" ? "Billo care search · demo" : "Case 8F2A · private demo record"}</strong>
        </div>

        {mode === "search" ? (
          <div className={styles.searchScreen}>
            <div className={styles.screenHeading}>
              <span>Before care</span>
              <h3>Compare care without the waiting room.</h3>
              <p>Try a real search. Synthetic results remain available if the local API is offline.</p>
            </div>
            <form className={styles.searchForm} onSubmit={compareCare}>
              <label>What happened?<input value={query} maxLength={160} onChange={(event) => setQuery(event.target.value)} /></label>
              <label>Near<input value={near} maxLength={80} onChange={(event) => setNear(event.target.value)} /></label>
              <button type="submit" disabled={loading}>{loading ? "Comparing…" : "Compare care"}</button>
            </form>
            <div className={styles.results} aria-live="polite" aria-busy={loading}>
              {places.map((place, index) => (
                <article key={`${place.name}-${index}`}>
                  <span className={styles.number}>{String(index + 1).padStart(2, "0")}</span>
                  <div className={styles.provider}>
                    <div><h4>{place.name}</h4><span>{place.kind.replaceAll("_", " ")}</span></div>
                    <p>{place.address} · {place.hours}</p>
                    <small>{place.source}</small>
                  </div>
                  <div className={styles.price}><span>Typical</span><strong>{formatMoney(place.typical)}</strong><small>from {formatMoney(place.low)}</small></div>
                </article>
              ))}
            </div>
          </div>
        ) : (
          <div className={styles.caseScreen}>
            <nav aria-label="Case sections">
              {(["overview", "visit", "documents", "benefits"] as CaseTab[]).map((tab) => (
                <button key={tab} type="button" aria-current={caseTab === tab ? "page" : undefined} onClick={() => setCaseTab(tab)}>
                  {tab === "visit" ? "Visit log" : tab[0].toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </nav>
            <div className={styles.caseBody}>
              <div className={styles.caseTitle}><div><span>Westwood Urgent Care</span><h3>Knee injury visit</h3></div><strong>In review</strong></div>
              {caseTab === "overview" && (
                <>
                  <div className={styles.total}><div><span>Current organized total</span><small>Estimate was $240</small></div><strong>$360</strong></div>
                  <div className={styles.checks}>
                    <div><b>✓</b><span><strong>Provider matched</strong><small>NPI and location confirmed</small></span><em>Done</em></div>
                    <div><b>✓</b><span><strong>Receipt organized</strong><small>2 coded lines · no mismatch</small></span><em>Done</em></div>
                    <div><b>2</b><span><strong>Possible benefit paths</strong><small>HSA receipt · out-of-network claim</small></span><em>Review</em></div>
                  </div>
                </>
              )}
              {caseTab === "visit" && <SimulationList title="Visit log" rows={[["Office visit", "$240"], ["Knee X-ray", "$120"], ["Running total", "$360"]]} />}
              {caseTab === "documents" && <SimulationList title="Documents" rows={[["Itemized receipt", "Ready"], ["Visit summary", "Ready"], ["Payment receipt", "Waiting"]]} />}
              {caseTab === "benefits" && <SimulationList title="Possible benefit paths" rows={[["HSA reimbursement", "Review"], ["Out-of-network claim", "Possible"], ["Employer plan", "Ask first"]]} />}
            </div>
          </div>
        )}
      </div>
      <p className={styles.disclaimer}>Interactive simulation · providers, prices, case details, and payment states are synthetic.</p>
    </div>
  );
}

function SimulationList({ title, rows }: { title: string; rows: string[][] }) {
  return <div className={styles.simulationList}><h4>{title}</h4>{rows.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>;
}
