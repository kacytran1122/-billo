import Link from "next/link";

import { BilloLogo } from "@/components/BilloLogo";
import hv from "./JourneyScreen.module.css";

export const JOURNEY_STAGES = ["booked", "during", "verified", "payment"] as const;
export type JourneyStage = (typeof JOURNEY_STAGES)[number];

const STAGE_COPY: Record<JourneyStage, {
  eyebrow: string;
  title: string;
  description: string;
  status: string;
}> = {
  booked: {
    eyebrow: "Before care",
    title: "Your care plan is saved.",
    description: "Your selected provider, demo estimate, location, and reminder are together. Contact the provider to confirm an appointment.",
    status: "Selection saved",
  },
  during: {
    eyebrow: "During care",
    title: "Keep a live visit record.",
    description: "Log tests and services as they happen. Billo keeps a running demo estimate visible before the final bill arrives.",
    status: "Demo visit log",
  },
  verified: {
    eyebrow: "After care",
    title: "Your bill is organized.",
    description: "Extracted charges are compared with the visit record, and uncertain items are flagged for your review.",
    status: "Demo review",
  },
  payment: {
    eyebrow: "After care",
    title: "Approve only the right amount.",
    description: "The clinic, bill, and amount are checked once more before the simulated Visa payment step.",
    status: "Demo ready for review",
  },
};

function StageDetails({ stage }: { stage: JourneyStage }) {
  if (stage === "booked") {
    return (
      <>
        <article className={hv.primaryCard}>
          <span className={hv.cardLabel}>Selected care option</span>
          <h2>Westwood Urgent Care</h2>
          <dl className={hv.details}>
            <div><dt>Reminder</dt><dd>Tuesday · 3:30 PM</dd></div>
            <div><dt>Demo estimate</dt><dd>$180–$240</dd></div>
            <div><dt>Location</dt><dd>Westwood · 1.2 miles</dd></div>
          </dl>
        </article>
        <aside className={hv.sideCard}>
          <span className={hv.cardLabel}>Before you go</span>
          <ul><li>Care option saved</li><li>Calendar reminder ready</li><li>Provider confirmation required</li></ul>
        </aside>
      </>
    );
  }

  if (stage === "during") {
    return (
      <>
        <article className={hv.primaryCard}>
          <span className={hv.cardLabel}>Live visit log</span>
          <h2>2 services recorded</h2>
          <div className={hv.lineItems}>
            <div><span>Office visit</span><strong>$240</strong></div>
            <div><span>Knee X-ray</span><strong>≈ $120</strong></div>
          </div>
          <button className={hv.secondaryAction} type="button">+ Log another service</button>
        </article>
        <aside className={hv.totalCard}>
          <span className={hv.cardLabel}>Running demo estimate</span>
          <strong>$360</strong>
          <p>Based on the services recorded so far.</p>
        </aside>
      </>
    );
  }

  if (stage === "verified") {
    return (
      <>
        <article className={hv.primaryCard}>
          <span className={hv.cardLabel}>Demo line-by-line review</span>
          <h2>Sample charges extracted</h2>
          <div className={hv.lineItems}>
            <div><span>Office visit</span><strong>$240 · printed</strong></div>
            <div><span>Knee X-ray</span><strong>$120 · printed</strong></div>
            <div className={hv.totalLine}><span>Printed demo total</span><strong>$360</strong></div>
          </div>
        </article>
        <aside className={hv.sideCard}>
          <span className={hv.cardLabel}>Possible benefit path</span>
          <ul><li>HSA may apply</li><li>Itemized receipt needed</li><li>Plan administrator decides</li></ul>
        </aside>
      </>
    );
  }

  return (
    <>
      <article className={hv.primaryCard}>
        <span className={hv.cardLabel}>Final review</span>
        <h2>Westwood Urgent Care</h2>
        <dl className={hv.details}>
          <div><dt>Verified bill</dt><dd>BILLO-4821</dd></div>
          <div><dt>Payment amount</dt><dd>$360.00</dd></div>
          <div><dt>Payment rail</dt><dd>Visa · simulated</dd></div>
        </dl>
      </article>
      <aside className={hv.approvalCard}>
        <span className={hv.cardLabel}>You stay in control</span>
        <strong>$360.00</strong>
        <button type="button">Approve simulated payment</button>
        <small>No real payment is submitted.</small>
      </aside>
    </>
  );
}

export default function JourneyScreen({ stage }: { stage: JourneyStage }) {
  const copy = STAGE_COPY[stage];

  return (
    <main className={`${hv.page} ${hv[stage]}`}>
      <header className={hv.header}>
        <Link className={hv.brand} href="/">
          <BilloLogo size={32} />
          <span>billo</span>
        </Link>
        <Link className={hv.close} href="/#pages" aria-label="Return to the Billo journey">×</Link>
      </header>

      <section className={hv.hero}>
        <div>
          <span className={hv.eyebrow}>{copy.eyebrow}</span>
          <h1>{copy.title}</h1>
          <p>{copy.description}</p>
        </div>
        <div className={hv.status}><span />{copy.status}</div>
      </section>

      <section className={hv.workspace} aria-label={`${copy.eyebrow} details`}>
        <StageDetails stage={stage} />
      </section>

      <footer className={hv.footer}>
        <Link href="/#pages">← Back to before, during, after</Link>
      </footer>
    </main>
  );
}
