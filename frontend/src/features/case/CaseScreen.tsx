import Link from "next/link";

import { BilloLogo } from "@/components/BilloLogo";
import { caseDataLabel, documentNeedsReview, documentReviewTitle, type CaseView, formatMoney, isDemoMode, safeWebUrl } from "@/lib/case-view";
import styles from "./CaseScreen.module.css";

function DataBadge({ mode }: { mode: string }) {
  const demo = isDemoMode(mode);
  const badgeClass = mode === "mixed" ? styles.mixedBadge : demo ? styles.demoBadge : styles.liveBadge;
  return <span className={`${styles.badge} ${badgeClass}`}>{caseDataLabel(mode)}</span>;
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}

function SectionHeading({ id, number, title, state }: { id: string; number: string; title: string; state: string }) {
  return (
    <div className={styles.sectionHeading}>
      <span>{number}</span>
      <div><h2 id={id}>{title}</h2><p>{state}</p></div>
    </div>
  );
}

function documentSource(reader?: string) {
  if (reader === "demo" || reader === "demo_fallback") return "Demo document";
  if (reader === "ocr" || reader === "vision") return "Patient-provided document";
  return "Document source unconfirmed";
}

export function CaseScreen({ view }: { view: CaseView }) {
  const estimate = view.estimate;
  const currency = estimate?.currency || view.document?.currency || view.visit?.currency || "USD";
  const items = view.visit?.items || [];
  const hasVisit = items.length > 0;
  const hasDocument = Boolean(view.document);
  const visitTotal = view.visit?.running_total ?? estimate?.amount ?? 0;
  const calendarUrl = safeWebUrl(view.calendar?.ics_url);
  const googleCalendarUrl = safeWebUrl(view.calendar?.google_url, ["calendar.google.com"]);
  const directionsUrl = safeWebUrl(view.provider?.directions_url, ["www.google.com", "maps.google.com"]);
  const walletUrl = safeWebUrl(view.wallet_url);
  const providerTitle = view.provider?.name || documentReviewTitle(view.document?.type);
  const hasBeforeAction = Boolean(calendarUrl || googleCalendarUrl || directionsUrl);
  const reviewNeeded = documentNeedsReview(view.document);

  return (
    <main className={styles.page}>
      <div className={styles.emergency}>If symptoms are severe or life-threatening, call 911 in the U.S. now.</div>
      <div className={styles.shell}>
        <header className={styles.header}>
          <Link className={styles.brand} href="/" aria-label="Billo home"><BilloLogo size={30} /><span>billo</span></Link>
          <span className={styles.private}>Private case link</span>
        </header>

        <section className={styles.visitHeader} aria-labelledby="case-title">
          <div className={styles.kicker}><DataBadge mode={view.data_mode} /><span>Care plan</span></div>
          <h1 id="case-title">{providerTitle}</h1>
          {(view.provider?.address || view.provider?.hours) && (
            <dl className={styles.providerDetails}>
              {view.provider?.address && <div><dt>Location</dt><dd>{view.provider.address}</dd></div>}
              {view.provider?.hours && <div><dt>Hours</dt><dd>{view.provider.hours}</dd></div>}
            </dl>
          )}
          {estimate ? (
            <>
              <div className={styles.estimateCard}>
                <div><span>Saved estimate</span><small>{estimate.source_label || "Conversation care estimate"}</small></div>
                <strong>{formatMoney(estimate.amount, currency)}</strong>
              </div>
              <p className={styles.disclaimer}>This is an estimate, not a provider quote or appointment confirmation. Confirm availability and price directly with the provider.</p>
            </>
          ) : (
            <div className={styles.estimateCard}>
              <div><span>No pre-visit estimate</span><small>This case began with a bill or receipt from the conversation.</small></div>
            </div>
          )}
        </section>

        <section className={styles.timeline} id="before" aria-labelledby="before-title">
          <SectionHeading id="before-title" number="01" title="Before care" state={estimate ? "Care plan saved" : "No pre-visit plan was saved"} />
          {hasBeforeAction ? (
            <div className={styles.actionGrid}>
              {calendarUrl && <a className={styles.primaryAction} href={calendarUrl}>Add reminder to calendar</a>}
              {googleCalendarUrl && <a className={styles.secondaryAction} href={googleCalendarUrl} target="_blank" rel="noreferrer">Open Google Calendar</a>}
              {directionsUrl && <a className={styles.secondaryAction} href={directionsUrl} target="_blank" rel="noreferrer">Get directions</a>}
            </div>
          ) : <EmptyState>No appointment or location was added to this conversation.</EmptyState>}
        </section>

        <section className={styles.timeline} id="during" aria-labelledby="during-title">
          <SectionHeading id="during-title" number="02" title="During care" state={hasVisit ? `${items.length} service${items.length === 1 ? "" : "s"} recorded` : "Waiting for a service update"} />
          {hasVisit ? (
            <div className={styles.lineItems}>
              {items.map((item, index) => (
                <div className={styles.lineItem} key={`${item.code || item.label}-${index}`}>
                  <div><strong>{item.label}</strong>{item.code && <small>Code {item.code}</small>}{item.qualifier && <small>{item.qualifier}</small>}</div>
                  <span>{item.amount == null ? "Not priced" : formatMoney(item.amount, item.currency || currency)}</span>
                </div>
              ))}
              <div className={`${styles.lineItem} ${styles.totalLine}`}><strong>Current estimated total</strong><span>{formatMoney(visitTotal, currency)}</span></div>
              <p className={styles.disclaimer}>Based on the saved estimate and services recorded in the conversation. The final bill may differ.</p>
            </div>
          ) : <EmptyState>Tell Billo which services you receive and this section will update from the conversation.</EmptyState>}
        </section>

        <section className={styles.timeline} id="after" aria-labelledby="after-title">
          <SectionHeading id="after-title" number="03" title="After care" state={hasDocument ? (reviewNeeded ? "Review needed" : "Document organized") : "Waiting for a bill or receipt"} />
          {view.document ? (
            <div className={styles.afterCard}>
              <div className={styles.statusRow}>
                <span className={`${styles.statusPill} ${reviewNeeded ? styles.reviewPill : ""}`}>{reviewNeeded ? "Review needed" : "Organized"}</span>
                <span className={styles.statusPill}>{view.document.payment_status === "paid" ? "Paid receipt" : view.document.payment_status === "unpaid" ? "Unpaid final bill" : "Payment status unconfirmed"}</span>
                <span>{documentSource(view.document.reader)}</span>
                <span>{view.document.provider_match ? "Provider matched" : "Provider needs review"}</span>
              </div>
              {(view.document.lines || []).map((line, index) => (
                <div className={`${styles.lineItem} ${line.needs_review ? styles.reviewLine : ""}`} key={`${line.code || line.label}-${index}`}>
                  <div>
                    <strong>{line.label}</strong>
                    {line.code && <small>Code {line.code}</small>}
                    {line.needs_review && <small className={styles.reviewLabel}>Review needed{line.line_no ? ` · line ${line.line_no}` : ""}</small>}
                    {line.review_reasons?.map((reason) => <small key={reason}>{reason}</small>)}
                  </div>
                  <span>{line.amount == null ? "Not priced" : formatMoney(line.amount, line.currency || currency)}</span>
                </div>
              ))}
              {view.document.fallback_reason && (
                <p className={styles.readerNote}>A backup reader was used because {view.document.fallback_reason}. Confirm any flagged values against the original document.</p>
              )}
              <dl className={styles.totals}>
                <div><dt>Document total</dt><dd>{formatMoney(view.document.total, currency)}</dd></div>
                {view.document.estimate_difference != null && <div><dt>Difference from saved estimate</dt><dd>{view.document.estimate_difference > 0 ? "+" : ""}{formatMoney(view.document.estimate_difference, currency)}</dd></div>}
              </dl>
              {view.document.next_steps && view.document.next_steps.length > 0 && (
                <div className={styles.nextSteps}><h3>Next steps</h3><ul>{view.document.next_steps.map((step) => <li key={step}>{step}</li>)}</ul></div>
              )}
              {walletUrl && <a className={styles.primaryAction} href={walletUrl}>Open approved wallet handoff</a>}
              <p className={styles.disclaimer}>Review extracted values against the original document. Billo does not replace the provider, insurer, or plan administrator.</p>
            </div>
          ) : <EmptyState>Send the final bill or receipt in the same chat. This page will show the organized result after review completes.</EmptyState>}
        </section>

        <footer className={styles.footer}>
          <p>Keep this link private. Anyone who has it may be able to view this case until it expires.</p>
          {view.updated_at && <p>Last updated {new Date(view.updated_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}</p>}
        </footer>
      </div>
    </main>
  );
}
