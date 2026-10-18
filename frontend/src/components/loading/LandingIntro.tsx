"use client";

import { useEffect, useState } from "react";

import { BilloLogo } from "@/components/BilloLogo";
import styles from "./LandingIntro.module.css";

type IntroState = "visible" | "leaving" | "hidden";

/** A short app-style launch screen shown before the landing page is revealed. */
export function LandingIntro() {
  const [state, setState] = useState<IntroState>("visible");

  useEffect(() => {
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const leaveTimer = window.setTimeout(() => setState("leaving"), reducedMotion ? 180 : 720);
    const hideTimer = window.setTimeout(() => {
      setState("hidden");
      document.body.style.overflow = previousOverflow;
    }, reducedMotion ? 240 : 1080);

    return () => {
      window.clearTimeout(leaveTimer);
      window.clearTimeout(hideTimer);
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  if (state === "hidden") return null;

  return (
    <div className={styles.intro} data-state={state} role="status" aria-label="Loading Billo">
      <div className={styles.brand}>
        <span className={styles.logo}><BilloLogo size={54} /></span>
        <span className={styles.name}>billo</span>
        <span className={styles.tagline}>Make every care dollar count</span>
        <span className={styles.track}><span /></span>
      </div>
    </div>
  );
}
