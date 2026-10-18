"use client";

import { useEffect, useMemo, useState } from "react";
import QRCode from "qrcode";

import { BilloLogo } from "@/components/BilloLogo";
import { type HandoffView, safeWebUrl } from "@/lib/case-view";
import styles from "./HandoffScreen.module.css";

const FINAL_STATES = new Set(["linked", "expired", "unknown", "used"]);

function statusCopy(status: string) {
  if (status === "linked") return { title: "WhatsApp is linked", detail: "Continue the same Billo case in WhatsApp." };
  if (status === "expired") return { title: "This handoff expired", detail: "Return to ASI:One and ask Billo for a new WhatsApp link." };
  if (status === "used") return { title: "This handoff was already used", detail: "For privacy, return to the original chat if this was not you." };
  if (status === "unknown") return { title: "This handoff is unavailable", detail: "Check the link or ask Billo to create a new one." };
  return { title: "Waiting for WhatsApp", detail: "Open WhatsApp and send the prepared one-time code. This page will update automatically." };
}

export function HandoffScreen({ token, initial }: { token: string; initial: HandoffView }) {
  const [view, setView] = useState(initial);
  const [qr, setQr] = useState("");
  const copy = statusCopy(view.status);
  const whatsappUrl = safeWebUrl(view.deep_link, ["wa.me"]);
  const expires = useMemo(() => {
    if (!view.expires_at) return "";
    const value = typeof view.expires_at === "number" ? view.expires_at * 1000 : view.expires_at;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }, [view.expires_at]);

  useEffect(() => {
    let active = true;
    setQr("");
    if (!whatsappUrl || view.status !== "waiting") return () => { active = false; };
    void QRCode.toDataURL(whatsappUrl, {
      errorCorrectionLevel: "M",
      margin: 2,
      width: 360,
      color: { dark: "#17241c", light: "#ffffff" },
    }).then((value) => { if (active) setQr(value); });
    return () => { active = false; };
  }, [whatsappUrl, view.status]);

  useEffect(() => {
    if (FINAL_STATES.has(view.status)) return;
    const poll = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/handoff/${encodeURIComponent(token)}`, { cache: "no-store" });
        if (!response.ok) return;
        setView(await response.json() as HandoffView);
      } catch { /* Keep the last trustworthy state during a transient network failure. */ }
    }, 3000);
    return () => window.clearInterval(poll);
  }, [token, view.status]);

  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="handoff-title">
        <header className={styles.header}><BilloLogo size={34} /><span>billo</span><b>ASI:One → WhatsApp</b></header>
        <div className={styles.intro}>
          <span className={styles.eyebrow}>Secure case handoff</span>
          <h1 id="handoff-title">Continue in WhatsApp</h1>
          <p>Your first message carries a one-time code so Billo can continue the same conversation context.</p>
        </div>

        {view.status === "waiting" && whatsappUrl ? (
          <div className={styles.handoffGrid}>
            <div className={styles.qrWrap}>{qr ? <img src={qr} alt="QR code to continue this Billo case in WhatsApp" /> : <span>Preparing QR…</span>}</div>
            <div className={styles.instructions}>
              <span>One-time code</span>
              <strong>{view.code || view.display_code || "Ready"}</strong>
              <p>Scan with your phone, or open WhatsApp on this device. Send the prepared message without changing the code.</p>
              <a href={whatsappUrl} rel="noreferrer">Open WhatsApp <span>→</span></a>
              {expires && <small>Expires at {expires}</small>}
            </div>
          </div>
        ) : null}

        {view.status === "waiting" && !whatsappUrl ? (
          <div className={styles.unavailable}><strong>WhatsApp is not configured yet.</strong><p>Return to ASI:One. Your case has not been moved or exposed.</p></div>
        ) : null}

        <div className={`${styles.status} ${styles[view.status] || ""}`} role="status" aria-live="polite">
          <span aria-hidden="true" />
          <div><strong>{copy.title}</strong><p>{copy.detail}</p></div>
        </div>
        <footer>This link contains no phone number or case ID. It expires automatically and can be claimed only once.</footer>
      </section>
    </main>
  );
}
