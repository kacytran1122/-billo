/**
 * Billo "classical" landing page (migrated from "Billo 4.html").
 * Editorial layout with a single hero chat (ASI:One or WhatsApp),
 * a step marquee, visit-link cards and the "what Billo never does" list.
 * No client state, so it renders as a server component.
 */
import { Fragment } from "react";

export type ChatApp = "ASI:One" | "WhatsApp";

const STEPS = [
  "Symptoms", "Emergency check", "Three nearby prices", "Book",
  "Saved estimate", "Visit log", "Photo of the bill", "Verified record",
];

const NEVERS = [
  "Move real money. Every payment step in this demo is a labeled simulation.",
  "Ask for your card number.",
  "Tell you that you qualify for a benefit. Each path is possible, not confirmed.",
  "Read a bill in a group chat. Bills and payments stay private.",
  "Approve anything for you. Silence never counts as a yes.",
  "Give medical, legal, insurance or tax advice.",
].map((text, i) => ({ text, num: String(i + 1).padStart(2, "0") }));

/** 7×7 decorative code used on the visit-link card. */
const QR_PATTERN = "1110111100100110101111010010010101011110101110111";
const QR = QR_PATTERN.split("").map((b) => (b === "1" ? "var(--color-text)" : "transparent"));

function MarqueeRow() {
  return (
    <>
      {STEPS.map((s, i) => (
        <span
          key={i}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 28,
            paddingRight: 28,
            fontFamily: "var(--font-heading)",
            fontSize: 30,
            fontStyle: i % 2 ? "italic" : "normal",
            whiteSpace: "nowrap",
          }}
        >
          {s}
          <span style={{ color: "var(--color-accent)", fontSize: 18 }}>✦</span>
        </span>
      ))}
    </>
  );
}

/** Two identical rows scrolled by -50% for a seamless loop. */
function Marquee() {
  return (
    <div style={{ display: "flex", width: "max-content", animation: "billo-marquee 38s linear infinite" }}>
      <MarqueeRow />
      <MarqueeRow />
    </div>
  );
}

export default function ClassicLanding({
  chatApp = "ASI:One",
  showMarquee = true,
}: {
  chatApp?: ChatApp;
  showMarquee?: boolean;
}) {
  const isAsi = chatApp === "ASI:One";
  const isIMessage = chatApp === "WhatsApp";
  const marquee = <Marquee />;
  const qr = QR;
  const nevers = NEVERS;

  return (
    <div className="page page--bg">
      <div style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", fontSize: "14px" }}>
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "9px 24px", display: "flex", gap: "10px", alignItems: "center" }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--color-accent-300)", flex: "none" }}>
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
            <path d="M12 9v4" />
            <path d="M12 17h.01" />
          </svg>
          <span>
            If this might be an emergency, call{" "}
            <a href="tel:911" style={{ color: "var(--color-accent-300)" }}>911</a>
            {" "}now. Billo does not handle emergencies.
          </span>
        </div>
      </div>
      <header style={{ maxWidth: "1200px", margin: "0 auto", padding: "22px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
        <a href="#" style={{ fontFamily: "var(--font-heading)", fontSize: "34px", fontStyle: "italic", fontWeight: "600", color: "var(--color-text)", textDecoration: "none", letterSpacing: "-.01em", display: "flex", alignItems: "baseline", gap: "2px" }}>
          Billo
          <span style={{ color: "var(--color-accent)" }}>.</span>
        </a>
        <nav style={{ display: "flex", gap: "28px", alignItems: "center", fontSize: "15px", flexWrap: "wrap" }}>
          <a href="#thread" style={{ color: "var(--color-text)", textDecoration: "none" }}>How it works</a>
          {" "}
          <a href="#pages" style={{ color: "var(--color-text)", textDecoration: "none" }}>What you get</a>
          {" "}
          <a href="#never" style={{ color: "var(--color-text)", textDecoration: "none" }}>What it never does</a>
          {" "}
          <a className="btn btn-primary" href="https://asi1.ai">Open ASI:One</a>
        </nav>
      </header>
      <section style={{ maxWidth: "1200px", margin: "0 auto", padding: "40px 24px 72px", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,460px),1fr))", gap: "56px", alignItems: "center" }}>
        <div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <span className="tag tag-outline">A care companion</span>
            {" "}
            <span className="tag tag-neutral">for people paying for care themselves</span>
          </div>
          <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(52px,7.4vw,96px)", lineHeight: ".95", letterSpacing: "-.02em", margin: "28px 0 0", textWrap: "balance" }}>
            Plan the care.{" "}
            <em style={{ color: "var(--color-accent-700)" }}>Organize</em>
            {" "}what comes next.
          </h1>
          <p style={{ fontSize: "19px", lineHeight: "1.6", maxWidth: "500px", margin: "28px 0 0", color: "var(--color-neutral-800)", textWrap: "pretty" }}>
            Search one place, book another, forget the estimate, get a bill you can't compare to anything. Billo keeps the thread — from{" "}
            <span style={{ borderBottom: "2px solid var(--color-accent)" }}>three nearby prices</span>
            {" "}to{" "}
            <span style={{ borderBottom: "2px solid var(--color-accent)" }}>a bill checked against what you expected</span>
            .
          </p>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "36px" }}>
            <a className="btn btn-primary" href="https://asi1.ai" style={{ minHeight: "52px", padding: "0 24px", fontSize: "16px", borderWidth: "1.5px" }}>
              Start in ASI:One{" "}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </a>
            {" "}
            <a className="btn btn-secondary" href="/#connect" style={{ minHeight: "52px", padding: "0 24px", fontSize: "16px" }}>Text Billo on WhatsApp</a>
          </div>
          <p style={{ fontSize: "14px", color: "var(--color-neutral-700)", margin: "16px 0 0", fontStyle: "italic" }}>In ASI:One, search for Billo and tell it what happened.</p>
        </div>
        <div style={{ position: "relative", display: "flex", justifyContent: "center", padding: "20px 0" }}>
          <div style={{ position: "absolute", width: "420px", maxWidth: "92%", aspectRatio: "1", borderRadius: "50%", border: "1px solid var(--color-accent-300)", top: "50%", left: "50%", transform: "translate(-50%,-50%)" }} />
          <div style={{ position: "absolute", width: "540px", maxWidth: "110%", aspectRatio: "1", borderRadius: "50%", border: "1px dashed var(--color-divider)", top: "50%", left: "50%", transform: "translate(-50%,-50%)" }} />
          <div style={{ position: "relative", width: "310px", height: "640px", borderRadius: "50px", background: "var(--color-text)", padding: "11px", boxShadow: "var(--shadow-lg)", transform: "rotate(-2deg)" }}>
            <div style={{ width: "100%", height: "100%", borderRadius: "40px", background: "var(--color-neutral-100)", overflow: "hidden", display: "flex", flexDirection: "column", position: "relative" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 26px 6px", fontSize: "13px", fontWeight: "600", fontFamily: "var(--font-body)" }}>
                <span style={{ fontVariantNumeric: "tabular-nums" }}>9:41</span>
                <div style={{ width: "88px", height: "24px", borderRadius: "14px", background: "var(--color-text)" }} />
                <span style={{ fontSize: "11px" }}>●●●</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px 16px 12px", borderBottom: "1px solid var(--color-divider)" }}>
                <div style={{ width: "34px", height: "34px", borderRadius: "50%", border: "1.5px solid var(--color-accent)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "600", fontSize: "20px", color: "var(--color-accent-700)" }}>B</div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "18px", lineHeight: "1.1" }}>Billo</span>
                  {isIMessage && (
                    <span style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>WhatsApp · private chat</span>
                  )}
                  {isAsi && (
                    <span style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>ASI:One · Coordinator agent</span>
                  )}
                </div>
              </div>
              <div style={{ flex: "1", padding: "14px 12px", display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px", lineHeight: "1.45" }}>
                <div style={{ alignSelf: "flex-end", maxWidth: "78%", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "9px 13px", borderRadius: "16px 16px 4px 16px" }}>Twisted my knee on a run. It's swollen but I can walk on it.</div>
                <div style={{ alignSelf: "flex-start", maxWidth: "86%", border: "1px solid var(--color-divider)", background: "var(--color-bg)", padding: "9px 13px", borderRadius: "16px 16px 16px 4px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "var(--color-accent-700)", marginBottom: "4px", letterSpacing: ".04em", textTransform: "uppercase" }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                    Emergency check · clear
                  </div>
                  {" "}No emergency signs in what you told me. Three places nearby:
                </div>
                <div style={{ alignSelf: "flex-start", width: "90%", border: "1px solid var(--color-accent)", borderRadius: "12px", background: "var(--color-bg)", overflow: "hidden" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "9px 12px", borderBottom: "1px solid var(--color-divider)" }}>
                    <div>
                      <div style={{ fontWeight: "600" }}>Westwood Urgent Care</div>
                      <div style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>Open until 8 pm</div>
                    </div>
                    <div style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      <div style={{ fontFamily: "var(--font-heading)", fontSize: "20px", fontWeight: "600", lineHeight: "1" }}>$240</div>
                      <div style={{ fontSize: "10px", color: "var(--color-neutral-700)" }}>low $180</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "9px 12px", borderBottom: "1px solid var(--color-divider)" }}>
                    <div>
                      <div style={{ fontWeight: "600" }}>Campus Health Clinic</div>
                      <div style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>Open until 6 pm</div>
                    </div>
                    <div style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      <div style={{ fontFamily: "var(--font-heading)", fontSize: "20px", fontWeight: "600", lineHeight: "1" }}>$180</div>
                      <div style={{ fontSize: "10px", color: "var(--color-neutral-700)" }}>low $120</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "9px 12px" }}>
                    <div>
                      <div style={{ fontWeight: "600" }}>Santa Monica ER</div>
                      <div style={{ fontSize: "11px", color: "var(--color-neutral-700)" }}>Open 24 hours</div>
                    </div>
                    <div style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      <div style={{ fontFamily: "var(--font-heading)", fontSize: "20px", fontWeight: "600", lineHeight: "1" }}>$1,800</div>
                      <div style={{ fontSize: "10px", color: "var(--color-neutral-700)" }}>low $1,200</div>
                    </div>
                  </div>
                </div>
                <div style={{ alignSelf: "flex-end", maxWidth: "78%", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "9px 13px", borderRadius: "16px 16px 4px 16px" }}>Book Westwood.</div>
                <div style={{ alignSelf: "flex-start", maxWidth: "86%", border: "1px solid var(--color-divider)", background: "var(--color-bg)", padding: "9px 13px", borderRadius: "16px 16px 16px 4px" }}>
                  Booked. I saved your{" "}
                  <strong style={{ fontWeight: "600", borderBottom: "2px solid var(--color-accent)" }}>$240.00 estimate</strong>
                  {" "}and added the visit to your calendar.
                </div>
              </div>
              <div style={{ padding: "10px 12px 18px", display: "flex", gap: "8px", alignItems: "center" }}>
                <div style={{ flex: "1", border: "1px solid var(--color-divider)", borderRadius: "20px", padding: "9px 14px", fontSize: "12px", color: "var(--color-neutral-600)" }}>Tell Billo what happened…</div>
                <div style={{ width: "34px", height: "34px", borderRadius: "50%", border: "1.5px solid var(--color-accent)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-accent-700)" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
                    <circle cx="12" cy="13" r="3" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
          <div style={{ position: "absolute", left: "0", top: "18%", background: "var(--color-bg)", border: "1px solid var(--color-accent)", borderRadius: "var(--radius-lg)", padding: "12px 16px", boxShadow: "var(--shadow-md)", transform: "rotate(-4deg)" }}>
            <div style={{ fontSize: "11px", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>Saved estimate</div>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "34px", lineHeight: "1", fontVariantNumeric: "tabular-nums", marginTop: "2px" }}>$240.00</div>
          </div>
          <div style={{ position: "absolute", right: "0", bottom: "16%", background: "var(--color-bg)", border: "1px solid var(--color-divider)", borderRadius: "var(--radius-lg)", padding: "12px 16px", boxShadow: "var(--shadow-md)", transform: "rotate(3deg)", display: "flex", gap: "10px", alignItems: "center", maxWidth: "220px" }}>
            <div style={{ width: "30px", height: "30px", borderRadius: "50%", border: "1.5px solid var(--color-accent)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-accent-700)", flex: "none" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </div>
            <div style={{ fontSize: "13px", lineHeight: "1.35" }}>Bill matches provider, estimate &amp; visit log</div>
          </div>
        </div>
      </section>
      {showMarquee && (
        <div style={{ borderTop: "1px solid var(--color-divider)", borderBottom: "1px solid var(--color-divider)", overflow: "hidden", padding: "18px 0" }}>{marquee}</div>
      )}
      <section id="thread" style={{ maxWidth: "1200px", margin: "0 auto", padding: "96px 24px 40px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,420px),1fr))", gap: "40px", alignItems: "end" }}>
          <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(40px,5vw,64px)", lineHeight: "1", margin: "0", letterSpacing: "-.01em", textWrap: "balance" }}>
            One chat.{" "}
            <em>The whole thread</em>
            , before and after the visit.
          </h2>
          <p style={{ fontSize: "17px", lineHeight: "1.65", margin: "0", textAlign: "justify", hyphens: "auto", color: "var(--color-neutral-800)" }}>The hard part isn't one bill — it's that nothing connects. Tell Billo what happened, and it carries what you learned before care into what arrives after it. Everything happens in one conversation, in ASI:One or WhatsApp.</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,250px),1fr))", gap: "0", marginTop: "64px", borderTop: "1px solid var(--color-text)" }}>
          <div style={{ padding: "28px 24px 28px 0", borderRight: "1px solid var(--color-divider)" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "56px", lineHeight: "1", color: "var(--color-accent)", fontVariantNumeric: "tabular-nums" }}>01</div>
            <h3 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "26px", margin: "18px 0 8px" }}>Check</h3>
            <p style={{ fontSize: "15px", lineHeight: "1.6", margin: "0", color: "var(--color-neutral-800)" }}>Tell Billo what is going on. It checks for emergency signs first.</p>
          </div>
          <div style={{ padding: "28px 24px", borderRight: "1px solid var(--color-divider)" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "56px", lineHeight: "1", color: "var(--color-accent)", fontVariantNumeric: "tabular-nums" }}>02</div>
            <h3 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "26px", margin: "18px 0 8px" }}>Compare</h3>
            <p style={{ fontSize: "15px", lineHeight: "1.6", margin: "0", color: "var(--color-neutral-800)" }}>Three nearby places, with typical and low prices from public price files.</p>
          </div>
          <div style={{ padding: "28px 24px", borderRight: "1px solid var(--color-divider)" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "56px", lineHeight: "1", color: "var(--color-accent)", fontVariantNumeric: "tabular-nums" }}>03</div>
            <h3 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "26px", margin: "18px 0 8px" }}>Book &amp; log</h3>
            <p style={{ fontSize: "15px", lineHeight: "1.6", margin: "0", color: "var(--color-neutral-800)" }}>Billo saves the estimate. During the visit, tell it what was done — an X-ray, a splint.</p>
          </div>
          <div style={{ padding: "28px 0 28px 24px" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "56px", lineHeight: "1", color: "var(--color-accent)", fontVariantNumeric: "tabular-nums" }}>04</div>
            <h3 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "26px", margin: "18px 0 8px" }}>Snap the bill</h3>
            <p style={{ fontSize: "15px", lineHeight: "1.6", margin: "0", color: "var(--color-neutral-800)" }}>Send a photo. Billo matches it to the provider, the estimate and your visit log.</p>
          </div>
        </div>
      </section>
      <section style={{ maxWidth: "1200px", margin: "0 auto", padding: "64px 24px 96px", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,440px),1fr))", gap: "64px", alignItems: "center" }}>
        <div style={{ background: "var(--color-surface)", padding: "14px", borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-sm)", transform: "rotate(1deg)", maxWidth: "460px", justifySelf: "center", width: "100%", boxSizing: "border-box" }}>
          <div style={{ background: "var(--color-neutral-100)", padding: "32px 30px 26px", border: "1px solid var(--color-divider)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "12px" }}>
              <h3 style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "28px", margin: "0" }}>Care record</h3>
              <span className="tag tag-accent">Verified</span>
            </div>
            <p style={{ fontSize: "13px", color: "var(--color-neutral-700)", margin: "4px 0 0", fontStyle: "italic" }}>Westwood Urgent Care (demo) · synthetic example</p>
            <div style={{ marginTop: "22px", fontSize: "15px", fontVariantNumeric: "tabular-nums" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", padding: "12px 0", borderTop: "1px dashed var(--color-divider)" }}>
                <div>
                  <div>Office visit</div>
                  <div style={{ fontSize: "12px", color: "var(--color-neutral-700)", fontStyle: "italic" }}>In your saved estimate</div>
                </div>
                <span>$240.00</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", padding: "12px 0", borderTop: "1px dashed var(--color-divider)" }}>
                <div>
                  <div>X-ray, knee</div>
                  <div style={{ fontSize: "12px", color: "var(--color-neutral-700)", fontStyle: "italic" }}>You logged it during the visit</div>
                </div>
                <span>$120.00</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", padding: "14px 0 0", borderTop: "1.5px solid var(--color-text)", alignItems: "baseline" }}>
                <span style={{ fontWeight: "600" }}>Total on the bill</span>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "34px", lineHeight: "1", borderBottom: "2px solid var(--color-accent)" }}>$360.00</span>
              </div>
            </div>
            <p style={{ margin: "22px 0 0", fontSize: "14px", lineHeight: "1.55", color: "var(--color-accent-800)" }}>$120.00 more than your saved estimate — and it's the X-ray you logged. No surprise.</p>
          </div>
        </div>
        <div>
          <div style={{ fontSize: "12px", letterSpacing: ".12em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>After care</div>
          <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(40px,5vw,60px)", lineHeight: "1.02", margin: "14px 0 0", textWrap: "balance" }}>
            A bill you can finally{" "}
            <em>compare to something.</em>
          </h2>
          <p style={{ fontSize: "17px", lineHeight: "1.65", margin: "24px 0 0", maxWidth: "480px", textAlign: "justify", hyphens: "auto", color: "var(--color-neutral-800)" }}>Billo reads the final bill or paid receipt and lines it up against what you expected. If it's unpaid, it verifies the clinic's payment QR before you approve anything. If it's paid, it looks at a benefit only when you name one, like an HSA.</p>
        </div>
      </section>
      <section id="pages" style={{ borderTop: "1px solid var(--color-divider)", background: "var(--color-surface)" }}>
        <div style={{ maxWidth: "1320px", margin: "0 auto", padding: "96px 24px 112px" }}>
          <div style={{ textAlign: "center", maxWidth: "680px", margin: "0 auto" }}>
            <div style={{ fontSize: "12px", letterSpacing: ".12em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>What Billo sends you</div>
            <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(40px,5vw,64px)", lineHeight: "1", margin: "14px 0 0" }}>
              One link per visit,{" "}
              <em>always up to date.</em>
            </h2>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "40px 32px", marginTop: "72px" }}>
            <figure style={{ margin: "0", display: "flex", flexDirection: "column", alignItems: "center", gap: "20px" }}>
              <div style={{ width: "260px", height: "540px", borderRadius: "44px", background: "var(--color-text)", padding: "9px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box" }}>
                <div style={{ width: "100%", height: "100%", borderRadius: "36px", background: "var(--color-bg)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 4px" }}>
                    <div style={{ width: "76px", height: "20px", borderRadius: "12px", background: "var(--color-text)" }} />
                  </div>
                  <div style={{ padding: "14px 20px", display: "flex", flexDirection: "column", flex: "1" }}>
                    <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "600", fontSize: "20px" }}>
                      Billo
                      <span style={{ color: "var(--color-accent)" }}>.</span>
                    </span>
                    <h4 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "30px", lineHeight: "1", margin: "18px 0 0" }}>
                      Continue in{" "}
                      <em>WhatsApp</em>
                    </h4>
                    <p style={{ fontSize: "11.5px", lineHeight: "1.5", margin: "10px 0 0", color: "var(--color-neutral-800)" }}>
                      Scan with your phone camera. Your first message carries the code{" "}
                      <strong style={{ fontWeight: "600", letterSpacing: ".04em" }}>BILLO-4821</strong>
                      .
                    </p>
                    <div style={{ margin: "18px auto 0", width: "150px", height: "150px", padding: "10px", background: "var(--color-neutral-100)", border: "1px solid var(--color-accent)", borderRadius: "var(--radius-md)", boxSizing: "border-box", display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: "3px" }}>
                      {qr.map((c, cIndex) => (
                        <Fragment key={cIndex}>
                          <div style={{ background: c, borderRadius: "1px" }} />
                        </Fragment>
                      ))}
                    </div>
                    <div className="btn btn-primary" style={{ marginTop: "18px", fontSize: "13px" }}>Open in WhatsApp</div>
                    <div style={{ marginTop: "auto", padding: "10px 12px", border: "1px solid var(--color-divider)", borderRadius: "var(--radius-md)", fontSize: "11px", lineHeight: "1.45", display: "flex", gap: "8px", alignItems: "center" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "50%", border: "1.5px solid var(--color-accent)", flex: "none" }} />
                      Waiting for your first message. Works for 15 minutes.
                    </div>
                  </div>
                </div>
              </div>
              <figcaption style={{ textAlign: "center", maxWidth: "240px" }}>
                <div style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontWeight: "600" }}>Link page</div>
                <div style={{ fontSize: "13px", color: "var(--color-neutral-700)", fontStyle: "italic", marginTop: "2px" }}>Hand off from desktop to phone</div>
              </figcaption>
            </figure>
            <figure style={{ margin: "0", display: "flex", flexDirection: "column", alignItems: "center", gap: "20px" }}>
              <div style={{ width: "260px", height: "540px", borderRadius: "44px", background: "var(--color-text)", padding: "9px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box" }}>
                <div style={{ width: "100%", height: "100%", borderRadius: "36px", background: "var(--color-bg)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 4px" }}>
                    <div style={{ width: "76px", height: "20px", borderRadius: "12px", background: "var(--color-text)" }} />
                  </div>
                  <div style={{ padding: "14px 20px", display: "flex", flexDirection: "column", flex: "1" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "600", fontSize: "20px" }}>
                        Billo
                        <span style={{ color: "var(--color-accent)" }}>.</span>
                      </span>
                      <span className="tag tag-outline" style={{ fontSize: "10px" }}>Booked</span>
                    </div>
                    <h4 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "28px", lineHeight: "1", margin: "16px 0 0" }}>Westwood Urgent Care</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "10px", fontSize: "11px", color: "var(--color-neutral-700)" }}>
                      <span style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0" />
                          <circle cx="12" cy="10" r="3" />
                        </svg>
                        10833 Le Conte Ave, Los Angeles
                      </span>
                      {" "}
                      <span style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" />
                          <polyline points="12 6 12 12 16 14" />
                        </svg>
                        8am to 8pm
                      </span>
                    </div>
                    <div style={{ marginTop: "16px", padding: "14px", border: "1px solid var(--color-accent)", borderRadius: "var(--radius-md)" }}>
                      <div style={{ fontSize: "9.5px", letterSpacing: ".1em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>Saved estimate</div>
                      <div style={{ fontFamily: "var(--font-heading)", fontSize: "40px", lineHeight: "1", fontVariantNumeric: "tabular-nums", marginTop: "4px" }}>$240.00</div>
                      <div style={{ fontSize: "10.5px", lineHeight: "1.4", color: "var(--color-neutral-700)", marginTop: "6px" }}>Billo compares your final bill with it.</div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", marginTop: "12px" }}>
                      <div className="btn btn-primary" style={{ fontSize: "11px", padding: "6px 4px" }}>Add to calendar</div>
                      <div className="btn btn-secondary" style={{ fontSize: "11px", padding: "6px 4px" }}>Directions</div>
                    </div>
                    <div style={{ marginTop: "16px", borderTop: "1px solid var(--color-divider)", paddingTop: "10px" }}>
                      <div style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "16px" }}>During the visit</div>
                      <div style={{ fontSize: "10.5px", lineHeight: "1.45", color: "var(--color-neutral-700)", marginTop: "4px", fontStyle: "italic" }}>Nothing logged yet. Tell Billo what they do, like "they did an X-ray".</div>
                    </div>
                  </div>
                </div>
              </div>
              <figcaption style={{ textAlign: "center", maxWidth: "240px" }}>
                <div style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontWeight: "600" }}>Just booked</div>
                <div style={{ fontSize: "13px", color: "var(--color-neutral-700)", fontStyle: "italic", marginTop: "2px" }}>Address, hours and the estimate</div>
              </figcaption>
            </figure>
            <figure style={{ margin: "0", display: "flex", flexDirection: "column", alignItems: "center", gap: "20px", transform: "translateY(-24px)" }}>
              <div style={{ width: "260px", height: "540px", borderRadius: "44px", background: "var(--color-text)", padding: "9px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box" }}>
                <div style={{ width: "100%", height: "100%", borderRadius: "36px", background: "var(--color-bg)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 4px" }}>
                    <div style={{ width: "76px", height: "20px", borderRadius: "12px", background: "var(--color-text)" }} />
                  </div>
                  <div style={{ padding: "14px 20px", display: "flex", flexDirection: "column", flex: "1" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "600", fontSize: "20px" }}>
                        Billo
                        <span style={{ color: "var(--color-accent)" }}>.</span>
                      </span>
                      <span className="tag tag-accent" style={{ fontSize: "10px" }}>At the clinic</span>
                    </div>
                    <h4 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "28px", lineHeight: "1", margin: "16px 0 0" }}>Visit log</h4>
                    <p style={{ fontSize: "11px", color: "var(--color-neutral-700)", margin: "6px 0 0", fontStyle: "italic" }}>Westwood Urgent Care (demo)</p>
                    <div style={{ marginTop: "14px", fontSize: "12px", fontVariantNumeric: "tabular-nums" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderTop: "1px dashed var(--color-divider)" }}>
                        <span>Saved estimate</span>
                        <span>$240.00</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderTop: "1px dashed var(--color-divider)" }}>
                        <span>They did an x-ray</span>
                        <span>about $120.00</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "12px 0 0", borderTop: "1.5px solid var(--color-text)" }}>
                        <span style={{ fontWeight: "600" }}>Expected so far</span>
                        <span style={{ fontFamily: "var(--font-heading)", fontSize: "24px", borderBottom: "2px solid var(--color-accent)" }}>≈ $360</span>
                      </div>
                    </div>
                    <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                      <div style={{ alignSelf: "flex-end", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "7px 11px", borderRadius: "14px 14px 4px 14px" }}>they did an x-ray</div>
                      <div style={{ alignSelf: "flex-start", border: "1px solid var(--color-divider)", padding: "7px 11px", borderRadius: "14px 14px 14px 4px", maxWidth: "85%" }}>Logged — about $120. Your visit page is updated.</div>
                    </div>
                  </div>
                </div>
              </div>
              <figcaption style={{ textAlign: "center", maxWidth: "240px" }}>
                <div style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontWeight: "600" }}>During the visit</div>
                <div style={{ fontSize: "13px", color: "var(--color-neutral-700)", fontStyle: "italic", marginTop: "2px" }}>A running tally, in plain words</div>
              </figcaption>
            </figure>
            <figure style={{ margin: "0", display: "flex", flexDirection: "column", alignItems: "center", gap: "20px" }}>
              <div style={{ width: "260px", height: "540px", borderRadius: "44px", background: "var(--color-text)", padding: "9px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box" }}>
                <div style={{ width: "100%", height: "100%", borderRadius: "36px", background: "var(--color-bg)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 4px" }}>
                    <div style={{ width: "76px", height: "20px", borderRadius: "12px", background: "var(--color-text)" }} />
                  </div>
                  <div style={{ padding: "14px 20px", display: "flex", flexDirection: "column", flex: "1" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "600", fontSize: "20px" }}>
                        Billo
                        <span style={{ color: "var(--color-accent)" }}>.</span>
                      </span>
                      <span className="tag tag-outline" style={{ fontSize: "10px" }}>Amount due</span>
                    </div>
                    <h4 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "28px", lineHeight: "1", margin: "16px 0 0" }}>After the visit</h4>
                    <div style={{ marginTop: "14px", fontSize: "9.5px", letterSpacing: ".1em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>Total on the document</div>
                    <div style={{ fontFamily: "var(--font-heading)", fontSize: "44px", lineHeight: "1", fontVariantNumeric: "tabular-nums" }}>$360.00</div>
                    <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px", lineHeight: "1.4" }}>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <span style={{ color: "var(--color-accent-700)", flex: "none" }}>+</span>
                        <span>$120.00 more than your saved estimate — the X-ray you logged.</span>
                      </div>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--color-accent-700)", flex: "none", marginTop: "2px" }}>
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                        <span>The provider matches the place you booked.</span>
                      </div>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--color-accent-700)", flex: "none", marginTop: "2px" }}>
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                        <span>Keep this verified record with the original.</span>
                      </div>
                    </div>
                    <div className="btn btn-primary" style={{ marginTop: "auto", fontSize: "11.5px" }}>Open wallet handoff (simulation)</div>
                  </div>
                </div>
              </div>
              <figcaption style={{ textAlign: "center", maxWidth: "240px" }}>
                <div style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontWeight: "600" }}>Verified record</div>
                <div style={{ fontSize: "13px", color: "var(--color-neutral-700)", fontStyle: "italic", marginTop: "2px" }}>The bill, matched and explained</div>
              </figcaption>
            </figure>
            <figure style={{ margin: "0", display: "flex", flexDirection: "column", alignItems: "center", gap: "20px" }}>
              <div style={{ width: "260px", height: "540px", borderRadius: "44px", background: "var(--color-text)", padding: "9px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box" }}>
                <div style={{ width: "100%", height: "100%", borderRadius: "36px", background: "var(--color-bg)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 4px" }}>
                    <div style={{ width: "76px", height: "20px", borderRadius: "12px", background: "var(--color-text)" }} />
                  </div>
                  <div style={{ padding: "14px 20px", display: "flex", flexDirection: "column", flex: "1" }}>
                    <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "600", fontSize: "20px" }}>
                      Billo
                      <span style={{ color: "var(--color-accent)" }}>.</span>
                    </span>
                    <h4 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "28px", lineHeight: "1", margin: "16px 0 0" }}>Wallet handoff</h4>
                    <div style={{ marginTop: "12px", padding: "8px 10px", border: "1px dashed var(--color-accent)", borderRadius: "var(--radius-md)", fontSize: "10.5px", lineHeight: "1.4", color: "var(--color-accent-800)" }}>Simulation. No card data was collected and no money moved.</div>
                    <div style={{ marginTop: "16px", fontSize: "9.5px", letterSpacing: ".1em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>Amount</div>
                    <div style={{ fontFamily: "var(--font-heading)", fontSize: "44px", lineHeight: "1", fontVariantNumeric: "tabular-nums" }}>$310.00</div>
                    <div style={{ marginTop: "12px", fontSize: "11px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "8px 0", borderTop: "1px solid var(--color-divider)" }}>
                        <span style={{ color: "var(--color-neutral-700)" }}>Merchant</span>
                        <span style={{ fontWeight: "600", textAlign: "right" }}>Westwood Urgent Care</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "8px 0", borderTop: "1px solid var(--color-divider)" }}>
                        <span style={{ color: "var(--color-neutral-700)" }}>Invoice</span>
                        <span style={{ fontWeight: "600" }}>BILLO-demo2</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", padding: "8px 0", borderTop: "1px solid var(--color-divider)" }}>
                        <span style={{ color: "var(--color-neutral-700)" }}>Reference</span>
                        <span style={{ fontVariantNumeric: "tabular-nums" }}>qrv_dbf688…</span>
                      </div>
                    </div>
                    <div style={{ marginTop: "auto", display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "10.5px", lineHeight: "1.4", color: "var(--color-neutral-800)" }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--color-accent-700)", flex: "none" }}>
                        <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
                        <path d="m9 12 2 2 4-4" />
                      </svg>
                      <span>Merchant, amount, currency and invoice all match. You approved this in your chat.</span>
                    </div>
                  </div>
                </div>
              </div>
              <figcaption style={{ textAlign: "center", maxWidth: "240px" }}>
                <div style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontWeight: "600" }}>Wallet handoff</div>
                <div style={{ fontSize: "13px", color: "var(--color-neutral-700)", fontStyle: "italic", marginTop: "2px" }}>Only after you say yes</div>
              </figcaption>
            </figure>
          </div>
        </div>
      </section>
      <section id="never" style={{ maxWidth: "1200px", margin: "0 auto", padding: "104px 24px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,340px),1fr))", gap: "48px" }}>
          <div>
            <div style={{ fontSize: "12px", letterSpacing: ".12em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>Guardrails</div>
            <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(40px,5vw,60px)", lineHeight: "1", margin: "14px 0 0" }}>
              What Billo{" "}
              <em>never</em>
              {" "}does.
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,260px),1fr))", columnGap: "40px", gridColumn: "span 1" }}>
            {nevers.map((n, nIndex) => (
              <Fragment key={nIndex}>
                <div style={{ display: "flex", gap: "14px", padding: "16px 0", borderTop: "1px solid var(--color-divider)", fontSize: "15px", lineHeight: "1.55" }}>
                  <span style={{ fontFamily: "var(--font-heading)", fontSize: "20px", lineHeight: "1.1", color: "var(--color-accent)", fontVariantNumeric: "tabular-nums", flex: "none", width: "24px" }}>{n.num}</span>
                  <span>{n.text}</span>
                </div>
              </Fragment>
            ))}
          </div>
        </div>
      </section>
      <section style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", right: "-40px", bottom: "-140px", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "560px", lineHeight: "1", color: "transparent", WebkitTextStroke: "1px var(--color-accent-700)", pointerEvents: "none" }}>B</div>
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "120px 24px", position: "relative" }}>
          <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(48px,7vw,96px)", lineHeight: ".95", margin: "0", maxWidth: "760px", textWrap: "balance" }}>
            Tell it{" "}
            <em style={{ color: "var(--color-accent-300)" }}>what happened.</em>
          </h2>
          <p style={{ fontSize: "18px", lineHeight: "1.6", maxWidth: "480px", margin: "24px 0 0", color: "var(--color-neutral-300)" }}>Billo checks for emergency indicators, shows clearly labeled nearby estimates, and keeps the case connected through bill review.</p>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "40px" }}>
            <a className="btn" href="https://asi1.ai" style={{ minHeight: "52px", padding: "0 24px", fontSize: "16px", color: "var(--color-accent-300)", border: "1.5px solid var(--color-accent-300)" }}>Start in ASI:One</a>
            {" "}
            <a className="btn" href="/#connect" style={{ minHeight: "52px", padding: "0 24px", fontSize: "16px", color: "var(--color-neutral-100)", border: "1px solid var(--color-neutral-700)" }}>Text Billo on WhatsApp</a>
          </div>
        </div>
        <footer style={{ maxWidth: "1200px", margin: "0 auto", padding: "28px 24px 40px", borderTop: "1px solid var(--color-neutral-800)", display: "flex", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", fontSize: "13px", color: "var(--color-neutral-400)", position: "relative" }}>
          <span>Built at LA Hacks 2026 on Fetch.ai agents, Photon WhatsApp, Tiger Data, Sentry and a Visa simulation.</span>
          {" "}
          <span>All patients and documents in the demo are synthetic.</span>
        </footer>
      </section>
    </div>
  );
}
