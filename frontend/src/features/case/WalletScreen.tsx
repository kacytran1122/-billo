import { BilloLogo } from "@/components/BilloLogo";
import { type WalletView, formatMoney, isDemoMode, safeWebUrl } from "@/lib/case-view";
import styles from "./WalletScreen.module.css";

function normalizedChecks(checks: WalletView["checks"]): Array<{ id?: string; label: string; passed: boolean }> {
  if (Array.isArray(checks)) return checks;
  return Object.entries(checks || {}).map(([label, passed]) => ({ label: label.replaceAll("_", " "), passed }));
}

export function WalletScreen({ view }: { view: WalletView }) {
  const demo = isDemoMode(view.mode);
  const checks = normalizedChecks(view.checks);
  const actionUrl = safeWebUrl(view.action_url);
  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="wallet-title">
        <header><div className={styles.brand}><BilloLogo size={32} /><span>billo</span></div><span className={demo ? styles.demo : styles.live}>{demo ? "Simulation" : "Live handoff"}</span></header>
        <div className={styles.hero}>
          <span>Wallet handoff</span>
          <h1 id="wallet-title">Review the approved payment</h1>
          <strong>{formatMoney(view.amount, view.currency || "USD")}</strong>
          <p>{view.merchant_name}</p>
        </div>
        <dl className={styles.details}>
          <div><dt>Merchant</dt><dd>{view.merchant_name}</dd></div>
          {view.invoice && <div><dt>Invoice</dt><dd>{view.invoice}</dd></div>}
          {view.reference && <div><dt>Reference</dt><dd>{view.reference}</dd></div>}
          <div><dt>Status</dt><dd>{view.status.replaceAll("_", " ")}</dd></div>
        </dl>
        {checks.length > 0 && <div className={styles.checks}><h2>Verification checks</h2>{checks.map((check) => <div key={check.id || check.label}><span aria-hidden="true">{check.passed ? "✓" : "!"}</span><p>{check.label}</p><strong>{check.passed ? "Matched" : "Review"}</strong></div>)}</div>}
        {actionUrl && !demo ? <a className={styles.action} href={actionUrl} rel="noreferrer">Continue to verified wallet</a> : <div className={styles.notice}><strong>{demo ? "No money moved" : "Handoff recorded"}</strong><p>{demo ? "This screen demonstrates the verified handoff. No card data was collected and no payment was submitted." : "No certified wallet destination is available. Return to the conversation before taking another action."}</p></div>}
        <footer>Payment details come from the organized bill and the QR review in your conversation. Never approve a different merchant or amount.</footer>
      </section>
    </main>
  );
}
