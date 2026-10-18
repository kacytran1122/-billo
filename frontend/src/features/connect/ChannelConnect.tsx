"use client";

import { useEffect, useState, type MouseEvent } from "react";
import QRCode from "qrcode";
import { BilloLogo } from "@/components/BilloLogo";
import { BilloWord } from "@/components/BilloWord";
import { IMESSAGE_URL } from "@/lib/channels";
import styles from "./ChannelConnect.module.css";

export type ConnectChannel = "asi" | "imessage";

export const ASI_ONE_URL = "https://asi1.ai/ai/agent1qdral3yqhqaa28czja8ddwf7kzgj4evwmpd39qjz3zuxwc64tucyus67y0z";

const CHANNELS: Readonly<Record<ConnectChannel, { label: string; status: string }>> = {
  asi: { label: "ASI:One", status: "Live agent" },
  imessage: { label: "iMessage", status: "Via Photon" },
};

function useQr(destination: string) {
  const [src, setSrc] = useState("");

  useEffect(() => {
    let active = true;
    setSrc("");
    if (!destination) return () => { active = false; };
    void QRCode.toDataURL(destination, {
      errorCorrectionLevel: "M",
      margin: 2,
      width: 360,
      color: { dark: "#201f1d", light: "#ffffff" },
    }).then((value) => {
      if (active) setSrc(value);
    });
    return () => { active = false; };
  }, [destination]);

  return src;
}

function ChannelPreview({ channel }: { channel: ConnectChannel }) {
  if (channel === "asi") {
    return (
      <div className={`${styles.phone} ${styles.asiPhone}`} aria-label="ASI:One Billo chat preview">
        <div className={styles.phoneTop}><span /><BilloLogo size={24} /><strong>Billo · ASI:One</strong></div>
        <div className={`${styles.bubble} ${styles.sent}`}>My knee hurts near UCLA.</div>
        <div className={`${styles.bubble} ${styles.received}`}>No emergency signs found. I found 3 nearby prices.</div>
        <div className={styles.miniResult}><span>Campus Health</span><strong>$180</strong></div>
        <div className={styles.miniResult}><span>Westwood Urgent</span><strong>$240</strong></div>
      </div>
    );
  }

  if (channel === "imessage") {
    return (
      <div className={`${styles.phone} ${styles.messagePhone}`} aria-label="iMessage Billo chat preview">
        <div className={styles.phoneTop}><span /><BilloLogo size={24} /><strong>Billo · iMessage</strong></div>
        <div className={`${styles.bubble} ${styles.blue}`}>@Billo check this bill</div>
        <div className={styles.receipt}><b>WESTWOOD URGENT CARE</b><span>Office visit&nbsp; $240</span><span>X-ray&nbsp; $120</span><strong>Total&nbsp; $360</strong></div>
        <div className={`${styles.bubble} ${styles.gray}`}>Matched to your visit. Total verified: $360.</div>
      </div>
    );
  }

  return null;
}

export function ChannelConnect({
  open,
  initialChannel,
  onClose,
}: {
  open: boolean;
  initialChannel: ConnectChannel;
  onClose: () => void;
}) {
  const channel = initialChannel;
  const destination = channel === "asi" ? ASI_ONE_URL : IMESSAGE_URL;
  const qr = useQr(destination);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  if (!open) return null;
  const stop = (event: MouseEvent) => event.stopPropagation();
  const current = CHANNELS[channel];

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <section className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="connect-title" onClick={stop}>
        <button className={styles.close} onClick={onClose} aria-label="Close connection options">×</button>
        <header className={styles.heading}>
          <span className={styles.eyebrow}>Secure channel access</span>
          <h2 id="connect-title">Chat with <BilloWord />.</h2>
          <p>Scan the QR code on another device or continue securely on this one.</p>
        </header>

        <div className={styles.body}>
          <ChannelPreview channel={channel} />
          <div className={styles.connectPanel}>
            <div className={styles.channelLine}>
              <span>{current.label}</span>
              <b>{destination ? current.status.toUpperCase() : "NEEDS SETUP"}</b>
            </div>
            {destination && qr && (
              <img className={styles.qr} src={qr} alt={`QR code to open Billo in ${current.label}`} />
            )}
            {destination && !qr && <div className={styles.qrLoading}>Building secure handoff…</div>}
            {destination && (
              <>
                <p className={styles.help}>{channel === "imessage" ? "Opens Messages with a greeting ready to send. No tag is needed in a direct chat. This shared Photon line currently requires an assigned participant; opening Messages alone does not authorize a new number." : "Opens Billo's public ASI:One agent profile."}</p>
                <a className={styles.openButton} href={destination} target={channel === "asi" ? "_blank" : undefined} rel={channel === "asi" ? "noreferrer" : undefined}>
                  Open {current.label} <span>→</span>
                </a>
              </>
            )}
            {!destination && (
              <div className={styles.notReady}>
                <strong>Messaging is not connected yet.</strong>
                <p>Use ASI:One while messaging access is being configured.</p>
              </div>
            )}
            <small className={styles.privacy}>Billo responds only after you contact it. Never include emergency information—call 911 instead.</small>
          </div>
        </div>
      </section>
    </div>
  );
}
