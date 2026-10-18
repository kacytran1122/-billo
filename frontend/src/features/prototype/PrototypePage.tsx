"use client";

/**
 * Billo clickable prototype (migrated from "Billo 2.html").
 * A phone frame with eight screens — landing, ASI:One chat, link page,
 * visit stages (booked / during / after), wallet and iMessage.
 * Deep-link a screen with a hash, e.g. /prototype#asi.
 */
import { Fragment, useEffect, useState } from "react";
import Link from "next/link";
import { BilloLogo } from "@/components/BilloLogo";
import { BilloWord } from "@/components/BilloWord";
import { QRCells } from "@/components/QRCells";
import { makeQR } from "@/lib/qr";
import hv from "./PrototypePage.module.css";

export const SCREENS = ["landing", "asi", "link", "v1", "v2", "v3", "wallet", "imsg"] as const;
export type Screen = (typeof SCREENS)[number];

const TAB_LABELS: Record<Screen, string> = {
  landing: "Landing",
  asi: "ASI:One",
  link: "Link page",
  v1: "Booked",
  v2: "During",
  v3: "After",
  wallet: "Wallet",
  imsg: "iMessage",
};

const QR = makeQR("BILLO-4821");

const isScreen = (s: string): s is Screen => (SCREENS as readonly string[]).includes(s);

export default function PrototypePage({ startScreen = "landing" }: { startScreen?: Screen }) {
  const [screen, setScreen] = useState<Screen>(startScreen);
  const [linked, setLinked] = useState(false);

  // Honour #hash deep links on load and when the hash changes.
  useEffect(() => {
    const sync = () => {
      const h = (location.hash || "").slice(1);
      if (isScreen(h)) setScreen(h);
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const go = (s: Screen) => () => setScreen(s);

  // Values the markup binds to (same names as the original design logic).
  const tabs = SCREENS.map((k) => ({ label: TAB_LABELS[k], active: screen === k, inactive: screen !== k, go: go(k) }));
  const stage = screen === "v1" ? 1 : screen === "v2" ? 2 : screen === "v3" ? 3 : 0;
  const stages = (["Booked", "During", "After"] as const).map((label, i) => ({
    label,
    done: stage > i,
    todo: stage <= i,
    go: go(`v${i + 1}` as Screen),
  }));
  const qr = QR;
  const isLanding = screen === "landing";
  const isLink = screen === "link";
  const isVisit = stage > 0;
  const isWallet = screen === "wallet";
  const isAsi = screen === "asi";
  const isIMessage = screen === "imsg";
  const stage1 = stage === 1;
  const stageGte2 = stage >= 2;
  const stageLt3 = stage < 3;
  const stage3 = stage === 3;
  const linkWaiting = !linked;
  const linkLinked = linked;
  const linkNow = () => setLinked(true);
  const goAsi = go("asi");
  const goIMsg = go("imsg");
  const goV1 = go("v1");
  const goV2 = go("v2");
  const goLink = go("link");
  const goWallet = go("wallet");
  const goVisit1 = go("v1");
  const goVisit3 = go("v3");

  return (
    <div className="page page--neutral-200">
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", gap: "28px", padding: "28px 16px 56px", boxSizing: "border-box" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "14px" }}>
          <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: "10px", color: "var(--color-text)", textDecoration: "none" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "7px", fontFamily: "var(--font-heading)", fontSize: "32px", fontWeight: "400", fontStyle: "normal", lineHeight: "1", letterSpacing: "-.02em" }}>
              <BilloLogo size={34} />
              <span style={{ display: "inline-flex", alignItems: "baseline" }}>billo</span>
            </span>
            {" "}
            <span style={{ fontStyle: "normal", fontWeight: "400", fontSize: "20px", color: "var(--color-neutral-700)" }}>screens</span>
          </Link>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "6px", background: "var(--color-neutral-100)", borderRadius: "99px", padding: "6px", boxShadow: "var(--shadow-sm)" }}>
            {tabs.map((t, tIndex) => (
              <Fragment key={tIndex}>
                {t.active && (
                  <button onClick={t.go} style={{ border: "0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "14px", padding: "8px 16px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)" }}>{t.label}</button>
                )}
                {t.inactive && (
                  <button className={hv.hover1} onClick={t.go} style={{ border: "0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "14px", padding: "8px 16px", borderRadius: "99px", background: "transparent", color: "var(--color-text)" }}>{t.label}</button>
                )}
              </Fragment>
            ))}
          </div>
        </div>
        <div style={{ width: "400px", maxWidth: "100%", height: "840px", borderRadius: "56px", background: "var(--color-text)", padding: "12px", boxSizing: "border-box", boxShadow: "var(--shadow-lg)", flex: "none" }}>
          <div style={{ width: "100%", height: "100%", borderRadius: "44px", background: "var(--color-neutral-100)", overflow: "hidden", position: "relative", display: "flex", flexDirection: "column" }}>
            <div style={{ position: "absolute", top: "10px", left: "50%", transform: "translateX(-50%)", width: "110px", height: "30px", borderRadius: "16px", background: "var(--color-text)", zIndex: "2" }} />
            <div style={{ flex: "1", overflowY: "auto", paddingTop: "48px" }}>
              {/* ============ LANDING ============ */}
              {isLanding && (
                <div data-screen-label="Landing" style={{ display: "flex", flexDirection: "column" }}>
                  <div style={{ margin: "0 16px", background: "var(--color-text)", color: "var(--color-neutral-100)", fontSize: "11.5px", borderRadius: "12px", padding: "8px 12px" }}>
                    Emergency? Call{" "}
                    <a href="tel:911" style={{ color: "var(--color-accent-300)" }}>911</a>
                    . Billo doesn't handle emergencies.
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-heading)", fontSize: "28px", fontWeight: "400", fontStyle: "normal", lineHeight: "1", letterSpacing: "-.02em" }}>
                      <BilloLogo size={29} />
                      <span style={{ display: "inline-flex", alignItems: "baseline" }}>billo</span>
                    </span>
                    <button onClick={goAsi} style={{ border: "1px solid var(--color-accent)", cursor: "pointer", background: "transparent", color: "var(--color-accent-700)", borderRadius: "99px", padding: "7px 14px", fontFamily: "var(--font-body)", fontSize: "12.5px" }}>Get started</button>
                  </div>
                  <div style={{ position: "relative", overflow: "hidden", padding: "20px 20px 30px", textAlign: "center" }}>
                    <div style={{ position: "absolute", width: "260px", height: "260px", borderRadius: "50%", background: "oklch(0.92 0.06 165)", left: "-110px", top: "150px" }} />
                    <div style={{ position: "absolute", width: "220px", height: "220px", borderRadius: "50%", background: "oklch(0.91 0.06 300)", right: "-90px", top: "10px" }} />
                    <div style={{ position: "relative", display: "inline-flex", gap: "6px", alignItems: "center", background: "var(--color-neutral-100)", border: "1px solid var(--color-divider)", borderRadius: "99px", padding: "4px 12px 4px 5px", fontSize: "11.5px" }}>
                      <span style={{ background: "oklch(0.90 0.06 50)", borderRadius: "99px", padding: "2px 8px" }}>New</span>
                      ASI:One{" "}
                      &amp;
                      {" "}iMessage
                    </div>
                    <h1 style={{ position: "relative", fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "58px", lineHeight: ".9", letterSpacing: "-.02em", margin: "18px 0 0" }}>
                      Make every care dollar{" "}
                      <em style={{ color: "var(--color-accent-700)" }}>count.</em>
                    </h1>
                    <p style={{ position: "relative", fontSize: "15px", lineHeight: "1.5", margin: "14px auto 0", maxWidth: "280px", color: "var(--color-neutral-800)" }}>Compare prices before. Check the bill after. All in one chat.</p>
                    <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: "8px", marginTop: "22px" }}>
                      <button onClick={goAsi} style={{ border: "0", cursor: "pointer", minHeight: "50px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", fontFamily: "var(--font-body)", fontSize: "15px" }}>Open in ASI:One</button>
                      <button onClick={goIMsg} style={{ cursor: "pointer", minHeight: "50px", borderRadius: "99px", background: "var(--color-neutral-100)", border: "1px solid var(--color-text)", color: "var(--color-text)", fontFamily: "var(--font-body)", fontSize: "15px", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="oklch(0.6 0.17 255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
                        </svg>
                        Text on iMessage
                      </button>
                    </div>
                    <div style={{ position: "relative", margin: "26px auto 0", width: "250px", background: "var(--color-neutral-100)", borderRadius: "24px", padding: "14px", boxShadow: "var(--shadow-lg)", textAlign: "left", display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px", lineHeight: "1.4", transform: "rotate(-2deg)" }}>
                      <div style={{ alignSelf: "flex-end", maxWidth: "85%", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "7px 11px", borderRadius: "14px 14px 4px 14px" }}>
                        <BilloWord />
                        {" "}twisted my knee
                      </div>
                      <div style={{ alignSelf: "flex-start", display: "inline-flex", gap: "5px", alignItems: "center", background: "oklch(0.92 0.06 165)", padding: "4px 10px", borderRadius: "99px", fontSize: "10.5px" }}>✓ No emergency signs</div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "oklch(0.94 0.08 95)", borderRadius: "12px", padding: "8px 11px" }}>
                        <span style={{ fontWeight: "600" }}>Westwood Urgent</span>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "20px" }}>$240</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid var(--color-divider)", borderRadius: "12px", padding: "8px 11px", marginRight: "40px" }}>
                        <span>Campus Health</span>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "20px" }}>$180</span>
                      </div>
                      <div style={{ position: "absolute", right: "-30px", top: "auto", bottom: "24px", background: "oklch(0.90 0.06 50)", borderRadius: "14px", padding: "7px 12px", boxShadow: "var(--shadow-md)", transform: "rotate(8deg)" }}>
                        <div style={{ fontSize: "9px", letterSpacing: ".08em", textTransform: "uppercase" }}>Expected</div>
                        <div style={{ fontFamily: "var(--font-heading)", fontSize: "24px", lineHeight: "1" }}>$240</div>
                      </div>
                      <div style={{ position: "absolute", left: "-24px", bottom: "-14px", background: "oklch(0.91 0.05 235)", borderRadius: "99px", padding: "6px 12px", boxShadow: "var(--shadow-md)", transform: "rotate(-5deg)", fontSize: "11px" }}>✓ Bill matches</div>
                    </div>
                  </div>
                  <div style={{ padding: "28px 16px 8px" }}>
                    <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "36px", lineHeight: ".95", margin: "0 4px", textAlign: "center" }}>
                      All you need is{" "}
                      <BilloWord />
                      .
                    </h2>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gridAutoRows: "1fr", gap: "10px", marginTop: "20px" }}>
                      <div style={{ background: "oklch(0.92 0.06 165)", borderRadius: "22px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px", minHeight: "130px" }}>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "21px", lineHeight: "1" }}>Safety first</span>
                        <span style={{ marginTop: "auto", background: "var(--color-neutral-100)", borderRadius: "99px", padding: "5px 10px", fontSize: "11px", alignSelf: "flex-start" }}>✓ Clear</span>
                      </div>
                      <div style={{ background: "oklch(0.94 0.08 95)", borderRadius: "22px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px", minHeight: "130px" }}>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "21px", lineHeight: "1" }}>3 care estimates</span>
                        <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "7px" }}>
                          <div>
                            <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "10px" }}>
                              <span>Campus</span>
                              <span style={{ fontVariantNumeric: "tabular-nums" }}>$120–$180</span>
                            </div>
                            <div style={{ position: "relative", height: "6px", borderRadius: "99px", background: "var(--color-neutral-100)", marginTop: "4px" }}>
                              <div style={{ position: "absolute", left: "6.67%", width: "3.33%", minWidth: "6px", top: "0", bottom: "0", borderRadius: "99px", background: "var(--color-text)" }} />
                            </div>
                          </div>
                          <div>
                            <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "10px" }}>
                              <span>Westwood</span>
                              <span style={{ fontVariantNumeric: "tabular-nums" }}>$180–$240</span>
                            </div>
                            <div style={{ position: "relative", height: "6px", borderRadius: "99px", background: "var(--color-neutral-100)", marginTop: "4px" }}>
                              <div style={{ position: "absolute", left: "10%", width: "3.33%", minWidth: "6px", top: "0", bottom: "0", borderRadius: "99px", background: "var(--color-text)" }} />
                            </div>
                          </div>
                          <div>
                            <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "10px" }}>
                              <span>ER</span>
                              <span style={{ fontVariantNumeric: "tabular-nums" }}>$1.2–1.8k</span>
                            </div>
                            <div style={{ position: "relative", height: "6px", borderRadius: "99px", background: "var(--color-neutral-100)", marginTop: "4px" }}>
                              <div style={{ position: "absolute", left: "66.67%", width: "33.33%", minWidth: "6px", top: "0", bottom: "0", borderRadius: "99px", background: "var(--color-text)" }} />
                            </div>
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "7.5px", color: "var(--color-neutral-700)", fontVariantNumeric: "tabular-nums" }}>
                            <span>$0</span>
                            <span>$1,800</span>
                          </div>
                        </div>
                      </div>
                      <div style={{ background: "oklch(0.90 0.06 50)", borderRadius: "22px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px", minHeight: "130px" }}>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "21px", lineHeight: "1" }}>Estimate saved</span>
                        <span style={{ marginTop: "auto", fontFamily: "var(--font-heading)", fontSize: "34px", lineHeight: "1" }}>$240</span>
                      </div>
                      <div style={{ background: "oklch(0.91 0.06 300)", borderRadius: "22px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px", minHeight: "130px" }}>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "21px", lineHeight: "1" }}>Log the visit</span>
                        <span style={{ marginTop: "auto", alignSelf: "flex-start", background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "12px 12px 12px 3px", padding: "6px 9px", fontSize: "10.5px" }}>
                          <BilloWord />
                          {" "}x-ray
                        </span>
                      </div>
                      <div style={{ background: "oklch(0.91 0.05 235)", borderRadius: "22px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px", minHeight: "130px" }}>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "21px", lineHeight: "1" }}>Snap the bill</span>
                        <div style={{ marginTop: "auto", alignSelf: "center", width: "70px", background: "var(--color-neutral-100)", borderRadius: "6px", padding: "7px", transform: "rotate(-5deg)", boxShadow: "var(--shadow-sm)" }}>
                          <div style={{ height: "2px", background: "var(--color-neutral-300)" }} />
                          <div style={{ height: "2px", background: "var(--color-neutral-300)", marginTop: "4px", width: "70%" }} />
                          <div style={{ fontSize: "9px", fontWeight: "600", marginTop: "5px", textAlign: "right" }}>$360</div>
                        </div>
                      </div>
                      <div style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "22px", padding: "16px", display: "flex", flexDirection: "column", gap: "14px", minHeight: "130px" }}>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "21px", lineHeight: "1" }}>
                          Matched{" "}
                          &amp;
                          <em style={{ color: "var(--color-accent-300)" }}>explained</em>
                        </span>
                        <span style={{ marginTop: "auto", fontFamily: "var(--font-heading)", fontSize: "20px" }}>240 + 120 = 360</span>
                      </div>
                    </div>
                  </div>
                  <div style={{ padding: "28px 16px 8px" }}>
                    <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "36px", lineHeight: ".95", margin: "0", textAlign: "center" }}>
                      Start in ASI:One.{" "}
                      <em>Continue in iMessage.</em>
                    </h2>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", marginTop: "18px" }}>
                      <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "14px", padding: "10px 12px", fontSize: "12px" }}>ASI:One</span>
                      {" "}
                      <span>→</span>
                      <button onClick={goLink} style={{ border: "0", cursor: "pointer", background: "oklch(0.94 0.08 95)", borderRadius: "14px", padding: "10px 12px", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--color-text)", letterSpacing: ".04em" }}>BILLO-4821</button>
                      <span>→</span>
                      {" "}
                      <span style={{ background: "oklch(0.6 0.17 255)", color: "#fff", borderRadius: "14px", padding: "10px 12px", fontSize: "12px" }}>iMessage</span>
                    </div>
                    <div style={{ marginTop: "12px", border: "1.5px solid var(--color-text)", borderRadius: "20px", padding: "12px", display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "6px", fontSize: "11.5px" }}>
                      <span style={{ width: "100%", textAlign: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "17px" }}>One shared case record</span>
                      {" "}
                      <span style={{ background: "oklch(0.90 0.06 50)", borderRadius: "99px", padding: "5px 11px" }}>Booking</span>
                      {" "}
                      <span style={{ background: "oklch(0.94 0.08 95)", borderRadius: "99px", padding: "5px 11px" }}>Expected prices</span>
                      {" "}
                      <span style={{ background: "oklch(0.91 0.05 235)", borderRadius: "99px", padding: "5px 11px" }}>Documents</span>
                      {" "}
                      <span style={{ background: "oklch(0.91 0.06 300)", borderRadius: "99px", padding: "5px 11px" }}>Benefits</span>
                      {" "}
                      <span style={{ background: "oklch(0.92 0.06 165)", borderRadius: "99px", padding: "5px 11px" }}>Status</span>
                    </div>
                  </div>
                  <div style={{ padding: "28px 16px 8px" }}>
                    <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "36px", lineHeight: ".95", margin: "0", textAlign: "center" }}>
                      Before, during,{" "}
                      <em>after.</em>
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "18px" }}>
                      <button onClick={goV1} style={{ border: "0", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", background: "oklch(0.90 0.06 50)", borderRadius: "26px", padding: "22px 20px", fontFamily: "var(--font-body)", fontSize: "17px", color: "var(--color-text)" }}>
                        <span>Just booked</span>
                        <span>→</span>
                      </button>
                      <button onClick={goV2} style={{ border: "0", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", background: "oklch(0.91 0.06 300)", borderRadius: "26px", padding: "22px 20px", fontFamily: "var(--font-body)", fontSize: "17px", color: "var(--color-text)" }}>
                        <span>During the visit</span>
                        <span>→</span>
                      </button>
                      <button onClick={goVisit3} style={{ border: "0", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", background: "oklch(0.92 0.06 165)", borderRadius: "26px", padding: "22px 20px", fontFamily: "var(--font-body)", fontSize: "17px", color: "var(--color-text)" }}>
                        <span>Verified record</span>
                        <span>→</span>
                      </button>
                      <button onClick={goWallet} style={{ border: "0", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", background: "oklch(0.94 0.08 95)", borderRadius: "26px", padding: "22px 20px", fontFamily: "var(--font-body)", fontSize: "17px", color: "var(--color-text)" }}>
                        <span>Pay, safely</span>
                        <span>→</span>
                      </button>
                    </div>
                  </div>
                  <div style={{ margin: "20px 12px 12px", background: "oklch(0.90 0.06 50)", borderRadius: "28px", padding: "36px 20px", textAlign: "center" }}>
                    <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "42px", lineHeight: ".9", margin: "0" }}>
                      Make every care dollar{" "}
                      <em>count.</em>
                    </h2>
                    <button onClick={goAsi} style={{ border: "0", cursor: "pointer", marginTop: "20px", minHeight: "48px", padding: "0 24px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", fontFamily: "var(--font-body)", fontSize: "14px" }}>
                      Start with{" "}
                      <BilloWord />
                    </button>
                  </div>
                  <p style={{ fontSize: "10.5px", color: "var(--color-neutral-700)", textAlign: "center", margin: "4px 20px 24px" }}>Built at LA Hacks 2026 · Demo data is synthetic.</p>
                </div>
              )}
              {/* ============ LINK PAGE ============ */}
              {isLink && (
                <div data-screen-label="Link page" style={{ padding: "8px 22px 32px", display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", fontSize: "11.5px", borderRadius: "12px", padding: "8px 12px" }}>
                    Emergency? Call{" "}
                    <a href="tel:911" style={{ color: "var(--color-accent-300)" }}>911</a>
                    . Billo doesn't handle emergencies.
                  </div>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-heading)", fontSize: "26px", fontWeight: "400", fontStyle: "normal", lineHeight: "1", letterSpacing: "-.02em" }}>
                    <BilloLogo size={27} />
                    <span style={{ display: "inline-flex", alignItems: "baseline" }}>billo</span>
                  </span>
                  <div style={{ background: "oklch(0.91 0.05 235)", borderRadius: "28px", padding: "26px 22px", display: "flex", flexDirection: "column", alignItems: "center", gap: "18px", textAlign: "center" }}>
                    <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "40px", lineHeight: ".95", margin: "0" }}>
                      Continue in{" "}
                      <em>iMessage</em>
                    </h1>
                    <div style={{ width: "200px", height: "200px", padding: "14px", background: "#fff", borderRadius: "20px", boxSizing: "border-box", display: "grid", gridTemplateColumns: "repeat(21,1fr)", gap: "0", boxShadow: "var(--shadow-md)" }}>
                      <QRCells cells={qr} />
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                      <span style={{ fontSize: "11px", letterSpacing: ".1em", textTransform: "uppercase" }}>Your code</span>
                      <span style={{ fontFamily: "var(--font-heading)", fontSize: "30px", letterSpacing: ".06em", fontVariantNumeric: "tabular-nums" }}>BILLO-4821</span>
                    </div>
                    <button onClick={linkNow} style={{ border: "0", cursor: "pointer", width: "100%", minHeight: "52px", borderRadius: "99px", background: "oklch(0.6 0.17 255)", color: "#fff", fontFamily: "var(--font-body)", fontSize: "16px", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
                      </svg>
                      Open in iMessage
                    </button>
                  </div>
                  {linkWaiting && (
                    <div style={{ display: "flex", gap: "12px", alignItems: "center", border: "1px dashed var(--color-text)", borderRadius: "18px", padding: "14px 16px", fontSize: "13.5px", lineHeight: "1.4" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "oklch(0.94 0.08 95)", border: "1.5px solid var(--color-text)", flex: "none" }} />
                      Waiting for your first message · works for 15 min
                    </div>
                  )}
                  {linkLinked && (
                    <div style={{ display: "flex", gap: "12px", alignItems: "center", background: "oklch(0.92 0.06 165)", borderRadius: "18px", padding: "14px 16px", fontSize: "13.5px", lineHeight: "1.4" }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                      Linked! Your case continues in iMessage.
                    </div>
                  )}
                  <p style={{ fontSize: "12px", color: "var(--color-neutral-700)", textAlign: "center", margin: "0" }}>Scan with your phone camera, or tap the button on your phone.</p>
                </div>
              )}
              {/* ============ VISIT PAGE (3 stages) ============ */}
              {isVisit && (
                <div data-screen-label="Visit page" style={{ padding: "8px 22px 32px", display: "flex", flexDirection: "column", gap: "18px" }}>
                  <div style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", fontSize: "11.5px", borderRadius: "12px", padding: "8px 12px" }}>
                    Emergency? Call{" "}
                    <a href="tel:911" style={{ color: "var(--color-accent-300)" }}>911</a>
                    . Billo doesn't handle emergencies.
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-heading)", fontSize: "26px", fontWeight: "400", fontStyle: "normal", lineHeight: "1", letterSpacing: "-.02em" }}>
                      <BilloLogo size={27} />
                      <span style={{ display: "inline-flex", alignItems: "baseline" }}>billo</span>
                    </span>
                    {" "}
                    <span style={{ display: "inline-flex", gap: "5px", alignItems: "center", border: "1px solid var(--color-divider)", borderRadius: "99px", padding: "4px 10px", fontSize: "11px" }}>
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <rect width="18" height="11" x="3" y="11" rx="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                      Private link
                    </span>
                  </div>
                  <div style={{ background: "oklch(0.90 0.06 50)", borderRadius: "28px", padding: "22px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "36px", lineHeight: ".95", margin: "0" }}>Westwood Urgent Care</h1>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", fontSize: "11.5px" }}>
                      <span style={{ display: "inline-flex", gap: "5px", alignItems: "center", background: "var(--color-neutral-100)", borderRadius: "99px", padding: "5px 10px" }}>
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0" />
                          <circle cx="12" cy="10" r="3" />
                        </svg>
                        10833 Le Conte Ave
                      </span>
                      {" "}
                      <span style={{ display: "inline-flex", gap: "5px", alignItems: "center", background: "var(--color-neutral-100)", borderRadius: "99px", padding: "5px 10px" }}>
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" />
                          <polyline points="12 6 12 12 16 14" />
                        </svg>
                        8am–8pm
                      </span>
                    </div>
                    <div style={{ background: "var(--color-neutral-100)", borderRadius: "20px", padding: "16px 18px" }}>
                      <div style={{ fontSize: "10.5px", letterSpacing: ".1em", textTransform: "uppercase" }}>Expected price</div>
                      <div style={{ fontFamily: "var(--font-heading)", fontSize: "56px", lineHeight: "1", fontVariantNumeric: "tabular-nums", marginTop: "2px" }}>$240.00</div>
                      <div style={{ fontSize: "12px", color: "var(--color-neutral-700)", marginTop: "6px" }}>Billo checks your final bill against this.</div>
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "6px" }}>
                    {stages.map((s, sIndex) => (
                      <Fragment key={sIndex}>
                        <button onClick={s.go} style={{ border: "0", cursor: "pointer", background: "transparent", padding: "0", display: "flex", flexDirection: "column", gap: "6px", fontFamily: "var(--font-body)", textAlign: "left", color: "var(--color-text)" }}>
                          {s.done && (
                            <div style={{ height: "6px", borderRadius: "99px", background: "var(--color-text)" }} />
                          )}
                          {s.todo && (
                            <div style={{ height: "6px", borderRadius: "99px", background: "var(--color-neutral-300)" }} />
                          )}
                          <span style={{ fontSize: "11.5px" }}>{s.label}</span>
                        </button>
                      </Fragment>
                    ))}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "22px", margin: "0" }}>Before you go</h2>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12.5px" }}>
                      <a href="#" style={{ display: "flex", gap: "8px", alignItems: "center", justifyContent: "center", minHeight: "46px", borderRadius: "16px", background: "var(--color-text)", color: "var(--color-neutral-100)", textDecoration: "none" }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect width="18" height="18" x="3" y="4" rx="2" />
                          <path d="M16 2v4M8 2v4M3 10h18" />
                        </svg>
                        Apple Calendar
                      </a>
                      {" "}
                      <a href="#" style={{ display: "flex", gap: "8px", alignItems: "center", justifyContent: "center", minHeight: "46px", borderRadius: "16px", background: "oklch(0.91 0.05 235)", color: "var(--color-text)", textDecoration: "none" }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect width="18" height="18" x="3" y="4" rx="2" />
                          <path d="M16 2v4M8 2v4M3 10h18" />
                        </svg>
                        Google Calendar
                      </a>
                      {" "}
                      <a href="#" style={{ display: "flex", gap: "8px", alignItems: "center", justifyContent: "center", minHeight: "46px", borderRadius: "16px", background: "oklch(0.92 0.06 165)", color: "var(--color-text)", textDecoration: "none" }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0" />
                          <circle cx="12" cy="10" r="3" />
                        </svg>
                        Directions
                      </a>
                      <button onClick={goLink} style={{ border: "0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "12.5px", display: "flex", gap: "8px", alignItems: "center", justifyContent: "center", minHeight: "46px", borderRadius: "16px", background: "oklch(0.91 0.06 300)", color: "var(--color-text)" }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
                        </svg>
                        On iPhone
                      </button>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "22px", margin: "0" }}>During the visit</h2>
                    {stage1 && (
                      <div style={{ border: "1.5px dashed oklch(0.75 0.08 300)", borderRadius: "20px", padding: "16px", display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}>
                        <span style={{ color: "var(--color-neutral-700)" }}>Nothing logged yet. Tell Billo what they do:</span>
                        {" "}
                        <span style={{ alignSelf: "flex-start", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "8px 14px", borderRadius: "16px 16px 16px 4px" }}>
                          <BilloWord />
                          {" "}they did an x-ray
                        </span>
                      </div>
                    )}
                    {stageGte2 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "13.5px", fontVariantNumeric: "tabular-nums" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", background: "var(--color-neutral-200)", borderRadius: "14px", padding: "12px 14px" }}>
                          <span>Expected price</span>
                          <span>$240.00</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", background: "oklch(0.91 0.06 300)", borderRadius: "14px", padding: "12px 14px" }}>
                          <span>They did an x-ray</span>
                          <span>≈ $120.00</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "10px 4px 0", borderTop: "1.5px solid var(--color-text)", marginTop: "4px" }}>
                          <span style={{ fontWeight: "600" }}>Expected so far</span>
                          <span style={{ fontFamily: "var(--font-heading)", fontSize: "32px" }}>≈ $360</span>
                        </div>
                      </div>
                    )}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "22px", margin: "0" }}>After the visit</h2>
                    {stageLt3 && (
                      <div style={{ border: "1.5px dashed oklch(0.75 0.06 235)", borderRadius: "20px", padding: "16px", display: "flex", gap: "12px", alignItems: "center", fontSize: "13px", lineHeight: "1.4" }}>
                        <div style={{ width: "40px", height: "40px", borderRadius: "12px", background: "oklch(0.91 0.05 235)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
                            <circle cx="12" cy="13" r="3" />
                          </svg>
                        </div>
                        <span>
                          Send a photo of the bill to{" "}
                          <BilloWord />
                          {" "}in a private chat.
                        </span>
                      </div>
                    )}
                    {stage3 && (
                      <div style={{ background: "oklch(0.92 0.06 165)", borderRadius: "24px", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: "10.5px", letterSpacing: ".1em", textTransform: "uppercase" }}>Total on the bill</span>
                          <span style={{ background: "oklch(0.90 0.06 50)", borderRadius: "99px", padding: "3px 10px", fontSize: "11px" }}>Amount due</span>
                        </div>
                        <div style={{ fontFamily: "var(--font-heading)", fontSize: "56px", lineHeight: "1", fontVariantNumeric: "tabular-nums" }}>$360.00</div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12.5px" }}>
                          <span style={{ background: "var(--color-neutral-100)", borderRadius: "99px", padding: "7px 12px" }}>+$120 vs expected · the X-ray you logged</span>
                          {" "}
                          <span style={{ background: "var(--color-neutral-100)", borderRadius: "99px", padding: "7px 12px" }}>✓ Provider matches your booking</span>
                        </div>
                        <button onClick={goWallet} style={{ border: "0", cursor: "pointer", marginTop: "4px", minHeight: "48px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", fontFamily: "var(--font-body)", fontSize: "14px" }}>Open wallet handoff (simulation)</button>
                      </div>
                    )}
                  </div>
                  <p style={{ fontSize: "11px", lineHeight: "1.5", color: "var(--color-neutral-700)", margin: "6px 0 0", textAlign: "center" }}>Private to your case — don't post this link. Prices are estimates from public price files, not a quote.</p>
                </div>
              )}
              {/* ============ WALLET ============ */}
              {isWallet && (
                <div data-screen-label="Wallet handoff" style={{ padding: "8px 22px 32px", display: "flex", flexDirection: "column", gap: "18px" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-heading)", fontSize: "26px", fontWeight: "400", fontStyle: "normal", lineHeight: "1", letterSpacing: "-.02em" }}>
                    <BilloLogo size={27} />
                    <span style={{ display: "inline-flex", alignItems: "baseline" }}>billo</span>
                  </span>
                  <div style={{ background: "oklch(0.94 0.08 95)", borderRadius: "28px", padding: "24px 22px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "40px", lineHeight: ".95", margin: "0" }}>
                      Wallet{" "}
                      <em>handoff</em>
                    </h1>
                    <div style={{ border: "1.5px dashed var(--color-text)", borderRadius: "14px", padding: "9px 12px", fontSize: "12px" }}>Simulation · no card data collected, no money moved</div>
                    <div style={{ background: "var(--color-neutral-100)", borderRadius: "20px", padding: "18px" }}>
                      <div style={{ fontSize: "10.5px", letterSpacing: ".1em", textTransform: "uppercase" }}>Amount</div>
                      <div style={{ fontFamily: "var(--font-heading)", fontSize: "60px", lineHeight: "1", fontVariantNumeric: "tabular-nums" }}>$310.00</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", fontSize: "13.5px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", padding: "12px 0", borderTop: "1px solid var(--color-divider)" }}>
                      <span style={{ color: "var(--color-neutral-700)" }}>Merchant</span>
                      <span style={{ textAlign: "right" }}>Westwood Urgent Care (demo)</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", padding: "12px 0", borderTop: "1px solid var(--color-divider)" }}>
                      <span style={{ color: "var(--color-neutral-700)" }}>Invoice</span>
                      <span>BILLO-demo2</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", padding: "12px 0", borderTop: "1px solid var(--color-divider)", borderBottom: "1px solid var(--color-divider)" }}>
                      <span style={{ color: "var(--color-neutral-700)" }}>Reference</span>
                      <span style={{ fontSize: "12px", fontVariantNumeric: "tabular-nums" }}>qrv_dbf6880887f05861</span>
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12.5px" }}>
                    <span style={{ background: "oklch(0.92 0.06 165)", borderRadius: "14px", padding: "10px 12px" }}>✓ Merchant</span>
                    {" "}
                    <span style={{ background: "oklch(0.92 0.06 165)", borderRadius: "14px", padding: "10px 12px" }}>✓ Exact amount</span>
                    {" "}
                    <span style={{ background: "oklch(0.92 0.06 165)", borderRadius: "14px", padding: "10px 12px" }}>✓ Currency</span>
                    {" "}
                    <span style={{ background: "oklch(0.92 0.06 165)", borderRadius: "14px", padding: "10px 12px" }}>✓ Invoice</span>
                  </div>
                  <div style={{ display: "flex", gap: "10px", alignItems: "center", background: "oklch(0.91 0.06 300)", borderRadius: "18px", padding: "14px 16px", fontSize: "13px" }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
                      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                    You approved this step in your chat.
                  </div>
                  <p style={{ fontSize: "11px", lineHeight: "1.5", color: "var(--color-neutral-700)", margin: "0", textAlign: "center" }}>In production this opens an approved Visa wallet. This demo isn't certified.</p>
                </div>
              )}
              {/* ============ ASI:ONE CHAT ============ */}
              {isAsi && (
                <div data-screen-label="ASI:One chat" style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "6px 18px 12px", borderBottom: "1px solid var(--color-divider)" }}>
                    <div style={{ width: "36px", height: "36px", borderRadius: "12px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <BilloLogo size={24} />
                    </div>
                    <div style={{ flex: "1" }}>
                      <div style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "19px", lineHeight: "1.1" }}>Billo</div>
                      <div style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>ASI:One · Coordinator agent</div>
                    </div>
                    <span style={{ background: "oklch(0.92 0.06 165)", borderRadius: "99px", padding: "3px 10px", fontSize: "10.5px" }}>Online</span>
                  </div>
                  <div style={{ flex: "1", padding: "16px 14px", display: "flex", flexDirection: "column", gap: "10px", fontSize: "13.5px", lineHeight: "1.45" }}>
                    <div style={{ alignSelf: "flex-end", maxWidth: "80%", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "9px 13px", borderRadius: "18px 18px 4px 18px" }}>
                      <BilloWord />
                      {" "}twisted my knee on a run. Swollen, but I can walk.
                    </div>
                    <div style={{ alignSelf: "flex-start", display: "inline-flex", gap: "6px", alignItems: "center", background: "oklch(0.92 0.06 165)", padding: "6px 12px", borderRadius: "99px", fontSize: "12px" }}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                      No emergency signs
                    </div>
                    <div style={{ alignSelf: "flex-start", maxWidth: "85%", background: "var(--color-bg)", border: "1px solid var(--color-divider)", padding: "9px 13px", borderRadius: "18px 18px 18px 4px" }}>Three places near you:</div>
                    <div style={{ alignSelf: "flex-start", width: "92%", display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "oklch(0.94 0.08 95)", borderRadius: "16px", padding: "11px 14px" }}>
                        <div>
                          <div style={{ fontWeight: "600" }}>Westwood Urgent Care</div>
                          <div style={{ fontSize: "11px" }}>until 8 pm · low $180</div>
                        </div>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "26px", fontVariantNumeric: "tabular-nums" }}>$240</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--color-bg)", border: "1px solid var(--color-divider)", borderRadius: "16px", padding: "11px 14px" }}>
                        <div>
                          <div style={{ fontWeight: "600" }}>Campus Health Clinic</div>
                          <div style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>until 6 pm · low $120</div>
                        </div>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "26px", fontVariantNumeric: "tabular-nums" }}>$180</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--color-bg)", border: "1px solid var(--color-divider)", borderRadius: "16px", padding: "11px 14px" }}>
                        <div>
                          <div style={{ fontWeight: "600" }}>Santa Monica ER</div>
                          <div style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>24 hours · low $1,200</div>
                        </div>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "26px", fontVariantNumeric: "tabular-nums" }}>$1,800</span>
                      </div>
                    </div>
                    <div style={{ alignSelf: "flex-end", maxWidth: "80%", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "9px 13px", borderRadius: "18px 18px 4px 18px" }}>
                      <BilloWord />
                      {" "}book Westwood
                    </div>
                    <div style={{ alignSelf: "flex-start", maxWidth: "88%", background: "oklch(0.90 0.06 50)", padding: "12px 14px", borderRadius: "18px 18px 18px 4px", display: "flex", flexDirection: "column", gap: "8px" }}>
                      <span>Care plan saved. Estimated price:</span>
                      {" "}
                      <span style={{ fontFamily: "var(--font-heading)", fontSize: "36px", lineHeight: "1", fontVariantNumeric: "tabular-nums" }}>$240.00</span>
                      <button onClick={goVisit1} style={{ alignSelf: "flex-start", border: "0", cursor: "pointer", background: "var(--color-neutral-100)", borderRadius: "99px", padding: "7px 14px", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--color-text)" }}>Open visit page →</button>
                    </div>
                  </div>
                  <div style={{ padding: "10px 14px 18px", display: "flex", gap: "8px", alignItems: "center", borderTop: "1px solid var(--color-divider)" }}>
                    <div style={{ flex: "1", border: "1px solid var(--color-divider)", borderRadius: "99px", padding: "11px 16px", fontSize: "13px", color: "var(--color-neutral-600)" }}>
                      <BilloWord />
                      {" "}tell it what happened…
                    </div>
                    <div style={{ width: "42px", height: "42px", borderRadius: "50%", background: "var(--color-text)", color: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m5 12 7-7 7 7" />
                        <path d="M12 19V5" />
                      </svg>
                    </div>
                  </div>
                </div>
              )}
              {/* ============ IMESSAGE CHAT ============ */}
              {isIMessage && (
                <div data-screen-label="iMessage chat" style={{ display: "flex", flexDirection: "column", minHeight: "100%", background: "#fff", fontFamily: "var(--font-body)" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px", padding: "2px 0 12px", background: "var(--color-neutral-100)", borderBottom: "1px solid var(--color-neutral-200)" }}>
                    <div style={{ width: "50px", height: "50px", borderRadius: "50%", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <BilloLogo size={34} />
                    </div>
                    <span style={{ fontSize: "12px" }}>Billo ›</span>
                  </div>
                  <div style={{ flex: "1", padding: "14px 14px", display: "flex", flexDirection: "column", gap: "6px", fontSize: "14px", lineHeight: "1.35" }}>
                    <div style={{ alignSelf: "center", fontSize: "11px", color: "var(--color-neutral-600)" }}>iMessage · Today 9:02 AM</div>
                    <div style={{ alignSelf: "flex-end", maxWidth: "78%", background: "oklch(0.6 0.17 255)", color: "#fff", padding: "8px 13px", borderRadius: "19px" }}>
                      <BilloWord />
                      {" "}BILLO-4821
                    </div>
                    <div style={{ alignSelf: "flex-start", maxWidth: "80%", background: "#e9e9eb", color: "#000", padding: "8px 13px", borderRadius: "19px" }}>Linked to your Westwood visit. Expected price: $240.</div>
                    <div style={{ alignSelf: "center", fontSize: "11px", color: "var(--color-neutral-600)", marginTop: "8px" }}>Today 4:12 PM</div>
                    <div style={{ alignSelf: "flex-end", maxWidth: "78%", background: "oklch(0.6 0.17 255)", color: "#fff", padding: "8px 13px", borderRadius: "19px" }}>
                      <BilloWord />
                      {" "}here's the bill
                    </div>
                    <div style={{ alignSelf: "flex-end", width: "150px", background: "var(--color-neutral-100)", border: "1px solid var(--color-neutral-300)", borderRadius: "16px", padding: "12px", transform: "rotate(2deg)" }}>
                      <div style={{ fontSize: "9.5px", fontWeight: "600", letterSpacing: ".06em" }}>WESTWOOD URGENT CARE</div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", marginTop: "8px" }}>
                        <span>Office visit</span>
                        <span>240.00</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", marginTop: "3px" }}>
                        <span>X-ray, knee</span>
                        <span>120.00</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: "600", marginTop: "6px", borderTop: "1px dashed var(--color-neutral-400)", paddingTop: "5px" }}>
                        <span>TOTAL</span>
                        <span>$360.00</span>
                      </div>
                    </div>
                    <div style={{ alignSelf: "flex-start", maxWidth: "82%", background: "#e9e9eb", color: "#000", padding: "8px 13px", borderRadius: "19px" }}>Matches Westwood. $240 expected + $120 X-ray you logged.</div>
                    <div style={{ alignSelf: "flex-start", background: "oklch(0.92 0.06 165)", color: "#000", padding: "12px 14px", borderRadius: "19px", width: "70%", display: "flex", flexDirection: "column", gap: "6px" }}>
                      <span style={{ fontSize: "10.5px", letterSpacing: ".06em", textTransform: "uppercase" }}>Verified record</span>
                      {" "}
                      <span style={{ fontFamily: "var(--font-heading)", fontSize: "34px", lineHeight: "1" }}>$360.00</span>
                      <button onClick={goVisit3} style={{ alignSelf: "flex-start", border: "0", cursor: "pointer", background: "#fff", borderRadius: "99px", padding: "6px 12px", fontSize: "12px", color: "#000" }}>View record →</button>
                    </div>
                    <div style={{ alignSelf: "flex-end", maxWidth: "70%", background: "oklch(0.6 0.17 255)", color: "#fff", padding: "8px 13px", borderRadius: "19px" }}>Perfect, thank you!</div>
                    <div style={{ alignSelf: "flex-end", fontSize: "10.5px", color: "var(--color-neutral-600)" }}>Delivered</div>
                  </div>
                  <div style={{ padding: "8px 12px 18px", display: "flex", gap: "8px", alignItems: "center" }}>
                    <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "var(--color-neutral-200)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "20px", color: "var(--color-neutral-700)" }}>+</div>
                    <div style={{ flex: "1", border: "1px solid var(--color-neutral-300)", borderRadius: "19px", padding: "8px 14px", fontSize: "13px", color: "var(--color-neutral-600)" }}>iMessage</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        <p style={{ fontSize: "13px", color: "var(--color-neutral-700)", margin: "0", fontStyle: "italic" }}>Tap the tabs, the progress bar or the buttons inside — screens link to each other.</p>
      </div>
    </div>
  );
}
