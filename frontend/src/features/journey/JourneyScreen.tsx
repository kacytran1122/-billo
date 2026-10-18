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
    title: "You’re booked.",
    description: "Your appointment, expected price, directions, and reminders are together in one place.",
    status: "Appointment confirmed",
  },
  during: {
    eyebrow: "During care",
    title: "Keep a live visit record.",
    description: "Log tests and services as they happen. Billo keeps the expected total visible before the bill arrives.",
    status: "Visit in progress",
  },
  verified: {
    eyebrow: "After care",
    title: "Your bill matches the visit.",
    description: "Every charge is matched to the care you recorded, with differences called out before payment.",
    status: "Record verified",
  },
  payment: {
    eyebrow: "After care",
    title: "Approve only the right amount.",
    description: "The clinic, bill, and amount are checked once more before the simulated Visa payment step.",
    status: "Ready for approval",
  },
};

function StageDetails({ stage }: { stage: JourneyStage }) {
  if (stage === "booked") {
    return (
      <>
        <article className={hv.primaryCard}>
          <span className={hv.cardLabel}>Appointment</span>
          <h2>Westwood Urgent Care</h2>
          <dl className={hv.details}>
            <div><dt>Date</dt><dd>Tuesday · 3:30 PM</dd></div>
            <div><dt>Expected</dt><dd>$180–$240</dd></div>
            <div><dt>Location</dt><dd>Westwood · 1.2 miles</dd></div>
          </dl>
        </article>
        <aside className={hv.sideCard}>
          <span className={hv.cardLabel}>Before you go</span>
          <ul><li>Appointment saved</li><li>Calendar reminder ready</li><li>Expected price saved</li></ul>
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
          <span className={hv.cardLabel}>Running estimate</span>
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
          <span className={hv.cardLabel}>Line-by-line check</span>
          <h2>Everything matches</h2>
          <div className={hv.lineItems}>
            <div><span>Office visit</span><strong>$240 ✓</strong></div>
            <div><span>Knee X-ray</span><strong>$120 ✓</strong></div>
            <div className={hv.totalLine}><span>Verified total</span><strong>$360</strong></div>
          </div>
        </article>
        <aside className={hv.sideCard}>
          <span className={hv.cardLabel}>Benefits check</span>
          <ul><li>HSA eligible</li><li>Itemized receipt ready</li><li>No duplicate charges found</li></ul>
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
