/**
 * Billo logo exploration board (migrated from "Billo 3.html").
 * Static design canvas: coin marks, seal arcs and wordmark directions
 * across several review rounds. Rendered as a server component.
 */
import { BilloLogo } from "@/components/BilloLogo";

export default function BrandBoard() {
  return (
    <div className="page page--neutral-200">
      <section style={{ padding: "56px 56px 0", display: "flex", flexDirection: "column", gap: "32px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "56px", margin: "0" }}>
          Coin o{" "}
          <em>— six ideas</em>
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "28px" }}>
          <div id="7a" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Milled edge</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>7a</span>
            </div>
            <div style={{ height: "260px", borderRadius: "24px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "16px", fontFamily: "var(--font-heading)", fontSize: "112px", lineHeight: "1", letterSpacing: "-.02em" }}>
                <BilloLogo size={108} />
                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  bill
                  <svg viewBox="0 0 56 56" style={{ width: ".62em", height: ".62em", marginLeft: ".04em", flex: "none", overflow: "visible" }}>
                    <circle cx="28" cy="28" r="25" fill="var(--color-accent)" stroke="var(--color-accent-700)" strokeWidth="5" strokeDasharray="2.2 2.2" />
                    <circle cx="28" cy="28" r="17" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2" />
                    <path d="M28 21 V35 M21 28 H35" stroke="var(--color-neutral-100)" strokeWidth="4" strokeLinecap="round" />
                  </svg>
                </span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg viewBox="0 0 56 56" width="56" height="56" style={{ overflow: "visible" }}>
                  <circle cx="28" cy="28" r="25" fill="var(--color-accent)" stroke="var(--color-accent-700)" strokeWidth="5" strokeDasharray="2.2 2.2" />
                  <circle cx="28" cy="28" r="17" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2" />
                  <path d="M28 21 V35 M21 28 H35" stroke="var(--color-neutral-100)" strokeWidth="4" strokeLinecap="round" />
                </svg>
              </div>
              <p style={{ flex: "1", margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Ridges like a real coin, with a tiny plus pressed in for care.</p>
            </div>
          </div>
          <div id="7b" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Spinning</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>7b</span>
            </div>
            <div style={{ height: "260px", borderRadius: "24px", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "16px", fontFamily: "var(--font-heading)", fontSize: "112px", lineHeight: "1", letterSpacing: "-.02em" }}>
                <BilloLogo size={108} />
                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  bill
                  <svg viewBox="0 0 56 56" style={{ width: ".62em", height: ".62em", marginLeft: ".04em", flex: "none", overflow: "visible" }}>
                    <ellipse cx="30" cy="30" rx="13" ry="25" fill="var(--color-accent-700)" />
                    <ellipse cx="26" cy="28" rx="13" ry="25" fill="var(--color-accent)" />
                    <ellipse cx="26" cy="28" rx="7" ry="17" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2" />
                    <path d="M48 6 L50 12 L56 14 L50 16 L48 22 L46 16 L40 14 L46 12 Z" fill="var(--color-text)" />
                  </svg>
                </span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg viewBox="0 0 56 56" width="56" height="56" style={{ overflow: "visible" }}>
                  <ellipse cx="30" cy="30" rx="13" ry="25" fill="var(--color-accent-700)" />
                  <ellipse cx="26" cy="28" rx="13" ry="25" fill="var(--color-accent)" />
                  <ellipse cx="26" cy="28" rx="7" ry="17" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2" />
                  <path d="M48 6 L50 12 L56 14 L50 16 L48 22 L46 16 L40 14 L46 12 Z" fill="var(--color-text)" />
                </svg>
              </div>
              <p style={{ flex: "1", margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A coin caught mid-flip, with a little sparkle.</p>
            </div>
          </div>
          <div id="7c" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Check coin</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>7c</span>
            </div>
            <div style={{ height: "260px", borderRadius: "24px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "16px", fontFamily: "var(--font-heading)", fontSize: "112px", lineHeight: "1", letterSpacing: "-.02em" }}>
                <BilloLogo size={108} />
                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  bill
                  <svg viewBox="0 0 56 56" style={{ width: ".62em", height: ".62em", marginLeft: ".04em", flex: "none", overflow: "visible" }}>
                    <circle cx="28" cy="28" r="26" fill="var(--color-accent)" />
                    <circle cx="28" cy="28" r="20" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2" strokeDasharray="1 4" strokeLinecap="round" />
                    <path d="M18 29 L25 36 L39 21" fill="none" stroke="var(--color-neutral-100)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg viewBox="0 0 56 56" width="56" height="56" style={{ overflow: "visible" }}>
                  <circle cx="28" cy="28" r="26" fill="var(--color-accent)" />
                  <circle cx="28" cy="28" r="20" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2" strokeDasharray="1 4" strokeLinecap="round" />
                  <path d="M18 29 L25 36 L39 21" fill="none" stroke="var(--color-neutral-100)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <p style={{ flex: "1", margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A coin with a check mark: the bill matched.</p>
            </div>
          </div>
          <div id="7d" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Coin stack</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>7d</span>
            </div>
            <div style={{ height: "260px", borderRadius: "24px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "16px", fontFamily: "var(--font-heading)", fontSize: "112px", lineHeight: "1", letterSpacing: "-.02em" }}>
                <BilloLogo size={108} />
                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  bill
                  <svg viewBox="0 0 56 56" style={{ width: ".62em", height: ".62em", marginLeft: ".04em", flex: "none", overflow: "visible" }}>
                    <ellipse cx="28" cy="46" rx="24" ry="8" fill="var(--color-accent-700)" />
                    <rect x="4" y="38" width="48" height="8" fill="var(--color-accent-700)" />
                    <ellipse cx="28" cy="38" rx="24" ry="8" fill="var(--color-accent)" />
                    <rect x="4" y="27" width="48" height="11" fill="var(--color-accent-700)" />
                    <ellipse cx="28" cy="27" rx="24" ry="8" fill="var(--color-accent)" />
                    <rect x="4" y="16" width="48" height="11" fill="var(--color-accent-700)" />
                    <ellipse cx="28" cy="16" rx="24" ry="8" fill="var(--color-accent)" />
                    <ellipse cx="28" cy="16" rx="15" ry="4.5" fill="none" stroke="var(--color-neutral-100)" strokeWidth="1.6" />
                  </svg>
                </span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg viewBox="0 0 56 56" width="56" height="56" style={{ overflow: "visible" }}>
                  <ellipse cx="28" cy="46" rx="24" ry="8" fill="var(--color-accent-700)" />
                  <rect x="4" y="38" width="48" height="8" fill="var(--color-accent-700)" />
                  <ellipse cx="28" cy="38" rx="24" ry="8" fill="var(--color-accent)" />
                  <rect x="4" y="27" width="48" height="11" fill="var(--color-accent-700)" />
                  <ellipse cx="28" cy="27" rx="24" ry="8" fill="var(--color-accent)" />
                  <rect x="4" y="16" width="48" height="11" fill="var(--color-accent-700)" />
                  <ellipse cx="28" cy="16" rx="24" ry="8" fill="var(--color-accent)" />
                  <ellipse cx="28" cy="16" rx="15" ry="4.5" fill="none" stroke="var(--color-neutral-100)" strokeWidth="1.6" />
                </svg>
              </div>
              <p style={{ flex: "1", margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Three coins stacked up: savings, adding up.</p>
            </div>
          </div>
          <div id="7e" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Heart cutout</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>7e</span>
            </div>
            <div style={{ height: "260px", borderRadius: "24px", background: "oklch(0.91 0.05 235)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "16px", fontFamily: "var(--font-heading)", fontSize: "112px", lineHeight: "1", letterSpacing: "-.02em" }}>
                <BilloLogo size={108} />
                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  bill
                  <svg viewBox="0 0 56 56" style={{ width: ".62em", height: ".62em", marginLeft: ".04em", flex: "none", overflow: "visible" }}>
                    <path fillRule="evenodd" fill="var(--color-accent)" d="M28 2 A26 26 0 1 1 27.99 2 Z M28 40 C19 34 15 28 18 23 C20.5 19 25.5 19.5 28 24 C30.5 19.5 35.5 19 38 23 C41 28 37 34 28 40 Z" />
                  </svg>
                </span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg viewBox="0 0 56 56" width="56" height="56" style={{ overflow: "visible" }}>
                  <path fillRule="evenodd" fill="var(--color-accent)" d="M28 2 A26 26 0 1 1 27.99 2 Z M28 40 C19 34 15 28 18 23 C20.5 19 25.5 19.5 28 24 C30.5 19.5 35.5 19 38 23 C41 28 37 34 28 40 Z" />
                </svg>
              </div>
              <p style={{ flex: "1", margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A coin with a heart punched through it.</p>
            </div>
          </div>
          <div id="7f" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Shiny</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>7f</span>
            </div>
            <div style={{ height: "260px", borderRadius: "24px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "16px", fontFamily: "var(--font-heading)", fontSize: "112px", lineHeight: "1", letterSpacing: "-.02em" }}>
                <BilloLogo size={108} />
                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  bill
                  <svg viewBox="0 0 56 56" style={{ width: ".62em", height: ".62em", marginLeft: ".04em", flex: "none", overflow: "visible" }}>
                    <circle cx="28" cy="28" r="26" fill="var(--color-accent)" />
                    <circle cx="28" cy="28" r="26" fill="none" stroke="var(--color-accent-700)" strokeWidth="3" />
                    <path d="M12 22 A17 17 0 0 1 24 11" fill="none" stroke="var(--color-neutral-100)" strokeWidth="4" strokeLinecap="round" />
                    <text x="29" y="38" textAnchor="middle" fontFamily="Times New Roman, Times, serif" fontStyle="italic" fontSize="28" fill="var(--color-neutral-100)">¢</text>
                  </svg>
                </span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg viewBox="0 0 56 56" width="56" height="56" style={{ overflow: "visible" }}>
                  <circle cx="28" cy="28" r="26" fill="var(--color-accent)" />
                  <circle cx="28" cy="28" r="26" fill="none" stroke="var(--color-accent-700)" strokeWidth="3" />
                  <path d="M12 22 A17 17 0 0 1 24 11" fill="none" stroke="var(--color-neutral-100)" strokeWidth="4" strokeLinecap="round" />
                  <text x="29" y="38" textAnchor="middle" fontFamily="Times New Roman, Times, serif" fontStyle="italic" fontSize="28" fill="var(--color-neutral-100)">¢</text>
                </svg>
              </div>
              <p style={{ flex: "1", margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A glossy coin with a shine and a ¢ mark.</p>
            </div>
          </div>
        </div>
      </section>
      <section style={{ padding: "56px 56px 0", display: "flex", flexDirection: "column", gap: "32px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "56px", margin: "0" }}>
          Final{" "}
          <em>— @ + heart coin</em>
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "28px" }}>
          <div id="6a" style={{ width: "1148px", maxWidth: "100%", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)", boxSizing: "border-box" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>
                @ coin + heart coin{" "}
                <span style={{ fontSize: "14px", background: "oklch(0.92 0.06 165)", borderRadius: "99px", padding: "3px 10px", marginLeft: "6px" }}>In use</span>
              </span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>6a</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "20px" }}>
              <div style={{ height: "320px", borderRadius: "24px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "22px", fontFamily: "var(--font-heading)", fontSize: "150px", lineHeight: "1", letterSpacing: "-.02em" }}>
                  <BilloLogo size={150} />
                  <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                    bill
                    <svg viewBox="0 0 56 56" style={{ width: ".56em", height: ".56em", marginLeft: ".04em", flex: "none" }} aria-hidden="true">
                      <circle cx="28" cy="28" r="26" fill="oklch(0.84 0.16 92)" />
                      <circle cx="28" cy="28" r="20" fill="none" stroke="var(--color-text)" strokeWidth="2" strokeDasharray="1 4" strokeLinecap="round" />
                      <path d="M28 39 C20 33.5 16.5 28.5 19 23.5 C21 19.5 25.5 19.8 28 24 C30.5 19.8 35 19.5 37 23.5 C39.5 28.5 36 33.5 28 39 Z" fill="var(--color-text)" />
                    </svg>
                  </span>
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div style={{ flex: "1", borderRadius: "24px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "10px", fontFamily: "var(--font-heading)", fontSize: "52px", lineHeight: "1", color: "var(--color-neutral-100)" }}>
                    <svg width="52" height="52" viewBox="0 0 100 100" style={{ flex: "none" }}>
                      <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" />
                      <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                      <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
                    </svg>
                    <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                      bill
                      <svg viewBox="0 0 56 56" style={{ width: ".56em", height: ".56em", marginLeft: ".04em", flex: "none" }} aria-hidden="true">
                        <circle cx="28" cy="28" r="26" fill="oklch(0.88 0.15 95)" />
                        <circle cx="28" cy="28" r="20" fill="none" stroke="var(--color-text)" strokeWidth="2" strokeDasharray="1 4" strokeLinecap="round" />
                        <path d="M28 39 C20 33.5 16.5 28.5 19 23.5 C21 19.5 25.5 19.8 28 24 C30.5 19.8 35 19.5 37 23.5 C39.5 28.5 36 33.5 28 39 Z" fill="var(--color-text)" />
                      </svg>
                    </span>
                  </span>
                </div>
                <div style={{ flex: "1", borderRadius: "24px", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center", gap: "20px" }}>
                  <div style={{ width: "96px", height: "96px", borderRadius: "24px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <BilloLogo size={64} />
                  </div>
                  <div style={{ width: "96px", height: "96px", borderRadius: "24px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "96px" }}>
                    <svg viewBox="0 0 56 56" style={{ width: ".62em", height: ".62em", flex: "none" }} aria-hidden="true">
                      <circle cx="28" cy="28" r="26" fill="oklch(0.88 0.15 95)" />
                      <circle cx="28" cy="28" r="20" fill="none" stroke="var(--color-text)" strokeWidth="2" strokeDasharray="1 4" strokeLinecap="round" />
                      <path d="M28 39 C20 33.5 16.5 28.5 19 23.5 C21 19.5 25.5 19.8 28 24 C30.5 19.8 35 19.5 37 23.5 C39.5 28.5 36 33.5 28 39 Z" fill="var(--color-text)" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>The @ from 1d, and the o is a yellow coin with a heart: care and money together. Both marks work alone as app icons.</p>
          </div>
        </div>
      </section>
      <section style={{ padding: "56px 56px 0", display: "flex", flexDirection: "column", gap: "32px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "56px", margin: "0" }}>
          Round 5{" "}
          <em>— more playful</em>
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "28px" }}>
          <div id="5a" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Bouncy</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>5a</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center", gap: "12px" }}>
              <svg width="96" height="96" viewBox="0 0 100 100" style={{ transform: "rotate(-10deg)" }}>
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
              </svg>
              <div style={{ display: "flex", alignItems: "flex-end", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "120px", lineHeight: "1" }}>
                <span style={{ display: "inline-block", transform: "rotate(-8deg) translateY(-6px)" }}>b</span>
                {" "}
                <span style={{ display: "inline-block", transform: "rotate(6deg) translateY(4px)", color: "oklch(0.55 0.14 300)" }}>i</span>
                {" "}
                <span style={{ display: "inline-block", transform: "rotate(-4deg) translateY(-10px)" }}>l</span>
                {" "}
                <span style={{ display: "inline-block", transform: "rotate(7deg)", color: "oklch(0.55 0.12 165)" }}>l</span>
                {" "}
                <span style={{ display: "inline-block", transform: "rotate(-6deg) translateY(-8px)", color: "var(--color-accent-700)" }}>o</span>
              </div>
            </div>
            <div style={{ height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", color: "var(--color-neutral-100)" }}>
              <svg width="40" height="40" viewBox="0 0 100 100" style={{ transform: "rotate(-10deg)" }}>
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
              </svg>
              <div style={{ display: "flex", alignItems: "flex-end", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "44px", lineHeight: "1" }}>
                <span style={{ display: "inline-block", transform: "rotate(-8deg) translateY(-2px)" }}>b</span>
                <span style={{ display: "inline-block", transform: "rotate(6deg) translateY(2px)", color: "oklch(0.85 0.08 300)" }}>i</span>
                <span style={{ display: "inline-block", transform: "rotate(-4deg) translateY(-4px)" }}>l</span>
                <span style={{ display: "inline-block", transform: "rotate(7deg)", color: "oklch(0.85 0.08 165)" }}>l</span>
                <span style={{ display: "inline-block", transform: "rotate(-6deg) translateY(-3px)", color: "var(--color-accent-300)" }}>o</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Bold letters that hop on the line, each in a different pastel.</p>
          </div>
          <div id="5b" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Bubble letters</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>5b</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "var(--color-neutral-200)", display: "flex", alignItems: "center", justifyContent: "center", gap: "5px", padding: "0 20px", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "46px", lineHeight: "1" }}>
              <span style={{ width: "68px", height: "68px", flex: "none", borderRadius: "50%", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", transform: "rotate(-8deg)" }}>
                <svg width="46" height="46" viewBox="0 0 100 100">
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="12" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
                </svg>
              </span>
              {" "}
              <span style={{ width: "68px", height: "68px", flex: "none", borderRadius: "50%", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center", transform: "translateY(-12px)" }}>b</span>
              {" "}
              <span style={{ width: "68px", height: "68px", flex: "none", borderRadius: "50%", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center", transform: "translateY(8px)" }}>i</span>
              {" "}
              <span style={{ width: "68px", height: "68px", flex: "none", borderRadius: "50%", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center", transform: "translateY(-8px)" }}>l</span>
              {" "}
              <span style={{ width: "68px", height: "68px", flex: "none", borderRadius: "50%", background: "oklch(0.91 0.05 235)", display: "flex", alignItems: "center", justifyContent: "center", transform: "translateY(10px)" }}>l</span>
              {" "}
              <span style={{ width: "68px", height: "68px", flex: "none", borderRadius: "50%", background: "var(--color-accent)", display: "flex", alignItems: "center", justifyContent: "center", transform: "translateY(-6px)", color: "var(--color-neutral-100)" }}>o</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "56px" }}>b</div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "4px", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "22px" }}>
                <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center" }}>b</span>
                <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center" }}>i</span>
                <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center" }}>l</span>
                <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "oklch(0.91 0.05 235)", display: "flex", alignItems: "center", justifyContent: "center" }}>l</span>
                <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--color-accent-300)", display: "flex", alignItems: "center", justifyContent: "center" }}>o</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Every letter is its own little coin. The last one is gold.</p>
          </div>
          <div id="5c" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Sticker</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>5c</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.91 0.05 235)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ position: "relative", transform: "rotate(-6deg)", background: "var(--color-neutral-100)", borderRadius: "999px", padding: "18px 40px 22px 30px", boxShadow: "0 0 0 6px var(--color-text),var(--shadow-lg)", display: "flex", alignItems: "center", gap: "10px" }}>
                <svg width="80" height="80" viewBox="0 0 100 100">
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="12" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "700", fontSize: "96px", lineHeight: "1", letterSpacing: "-.03em" }}>billo!</span>
                {" "}
                <span style={{ position: "absolute", right: "-18px", top: "-22px", width: "52px", height: "52px", borderRadius: "50%", background: "oklch(0.90 0.06 50)", border: "3px solid var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "24px", transform: "rotate(14deg)" }}>$</span>
              </div>
            </div>
            <div style={{ height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ transform: "rotate(-4deg)", background: "var(--color-neutral-100)", borderRadius: "999px", padding: "6px 18px 8px 12px", display: "flex", alignItems: "center", gap: "6px" }}>
                <svg width="32" height="32" viewBox="0 0 100 100">
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="12" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontWeight: "700", fontSize: "36px", lineHeight: "1" }}>billo!</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A tilted laptop sticker with a cheerful “!”.</p>
          </div>
          <div id="5d" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Coin hop</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>5d</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center", gap: "12px" }}>
              <svg width="96" height="96" viewBox="0 0 100 100">
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
              </svg>
              <div style={{ position: "relative", display: "flex", alignItems: "baseline", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "120px", lineHeight: "1", letterSpacing: "-.02em" }}>
                <span>bill</span>
                {" "}
                <span style={{ position: "relative", width: "62px", height: "62px", marginLeft: "6px", transform: "translateY(-62px)" }}>
                  <span style={{ position: "absolute", inset: "0", borderRadius: "50%", background: "var(--color-accent)", boxShadow: "inset 0 0 0 7px var(--color-accent-600)" }} />
                  <svg width="70" height="40" viewBox="0 0 70 40" style={{ position: "absolute", left: "-58px", top: "20px" }}>
                    <path d="M4 36 Q 24 4, 56 10" fill="none" stroke="var(--color-text)" strokeWidth="3" strokeLinecap="round" strokeDasharray="2 8" />
                  </svg>
                  <span style={{ position: "absolute", left: "8px", right: "8px", bottom: "-72px", height: "8px", borderRadius: "50%", background: "var(--color-text)", opacity: ".18" }} />
                </span>
              </div>
            </div>
            <div style={{ height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", color: "var(--color-neutral-100)", fontFamily: "var(--font-heading)", fontWeight: "700", fontSize: "44px" }}>
              <svg width="40" height="40" viewBox="0 0 100 100">
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
              </svg>
              <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                bill
                <span style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--color-accent-300)", marginLeft: "3px", transform: "translateY(-18px)" }} />
              </span>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>The o pops up like a coin flip.</p>
          </div>
        </div>
      </section>
      <section style={{ padding: "56px 56px 0", display: "flex", flexDirection: "column", gap: "32px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "56px", margin: "0" }}>
          Round 4{" "}
          <em>— @ + a special “billo”</em>
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "28px" }}>
          <div id="4a" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Coin o</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>4a</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: "14px", fontFamily: "var(--font-heading)", fontSize: "120px", lineHeight: "1", letterSpacing: "-.03em" }}>
                <svg width="104" height="104" viewBox="0 0 100 100" style={{ alignSelf: "center" }}>
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
                </svg>
                <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                  bill
                  <svg width="56" height="56" viewBox="0 0 56 56" style={{ marginLeft: "4px" }}>
                    <circle cx="28" cy="28" r="26" fill="var(--color-accent)" />
                    <circle cx="28" cy="28" r="17" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2.5" />
                  </svg>
                </span>
              </div>
            </div>
            <div style={{ height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", fontFamily: "var(--font-heading)", fontSize: "44px", color: "var(--color-neutral-100)", letterSpacing: "-.02em" }}>
              <svg width="40" height="40" viewBox="0 0 100 100">
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
              </svg>
              <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                bill
                <svg width="21" height="21" viewBox="0 0 56 56" style={{ marginLeft: "2px" }}>
                  <circle cx="28" cy="28" r="26" fill="var(--color-accent-300)" />
                </svg>
              </span>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>The o is a gold coin, matching the coin inside the @.</p>
          </div>
          <div id="4b" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Swash thread</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>4b</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                <svg width="100" height="100" viewBox="0 0 100 100">
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
                </svg>
                <div style={{ position: "relative", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "124px", lineHeight: "1", letterSpacing: "-.03em", paddingBottom: "18px" }}>
                  <span>b</span>
                  <span style={{ position: "relative" }}>
                    ı
                    <span style={{ position: "absolute", left: "50%", top: "22px", width: "18px", height: "18px", marginLeft: "-6px", borderRadius: "50%", background: "var(--color-accent)" }} />
                  </span>
                  <span>llo</span>
                  <svg width="230" height="30" viewBox="0 0 230 30" style={{ position: "absolute", left: "0", bottom: "0" }}>
                    <path d="M4 12 C 60 28, 150 28, 226 6" fill="none" stroke="var(--color-text)" strokeWidth="4" strokeLinecap="round" />
                  </svg>
                </div>
              </div>
            </div>
            <div style={{ height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", color: "var(--color-neutral-100)" }}>
              <svg width="40" height="40" viewBox="0 0 100 100">
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
              </svg>
              <div style={{ position: "relative", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "44px", lineHeight: "1", paddingBottom: "7px" }}>
                <span>b</span>
                <span style={{ position: "relative" }}>
                  ı
                  <span style={{ position: "absolute", left: "50%", top: "8px", width: "7px", height: "7px", marginLeft: "-2px", borderRadius: "50%", background: "var(--color-accent-300)" }} />
                </span>
                <span>llo</span>
                <svg width="82" height="11" viewBox="0 0 230 30" style={{ position: "absolute", left: "0", bottom: "0" }}>
                  <path d="M4 12 C 60 28, 150 28, 226 6" fill="none" stroke="var(--color-neutral-100)" strokeWidth="6" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Italic, with a coin for the i's dot and one line underneath: the thread.</p>
          </div>
          <div id="4c" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Two voices</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>4c</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px", fontFamily: "var(--font-heading)", fontSize: "124px", lineHeight: "1", letterSpacing: "-.03em" }}>
                <svg width="100" height="100" viewBox="0 0 100 100">
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
                </svg>
                <span>
                  <span>bi</span>
                  <em style={{ color: "var(--color-accent-700)" }}>llo</em>
                </span>
              </div>
            </div>
            <div style={{ height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", fontFamily: "var(--font-heading)", fontSize: "44px", color: "var(--color-neutral-100)", letterSpacing: "-.02em" }}>
              <svg width="40" height="40" viewBox="0 0 100 100">
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
              </svg>
              <span>
                <span>bi</span>
                <em style={{ color: "var(--color-accent-300)" }}>llo</em>
              </span>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Upright “bi”, gold italic “llo”: serious about bills, warm like “hello”.</p>
          </div>
        </div>
      </section>
      <section style={{ padding: "56px 56px 0", display: "flex", flexDirection: "column", gap: "32px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "56px", margin: "0" }}>
          Round 3{" "}
          <em>— friendlier</em>
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "28px" }}>
          <div id="3a" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Billo buddy</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>3a</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center", gap: "22px" }}>
              <svg width="170" height="170" viewBox="0 0 100 100">
                <path d="M50 10 C74 10 90 26 90 48 C90 70 74 84 50 84 C44 84 38 83 33 81 L16 90 L20 74 C13 67 10 58 10 48 C10 26 26 10 50 10 Z" fill="var(--color-neutral-100)" stroke="var(--color-text)" strokeWidth="5" strokeLinejoin="round" />
                <circle cx="38" cy="44" r="5" fill="var(--color-text)" />
                <circle cx="62" cy="44" r="5" fill="var(--color-text)" />
                <path d="M38 58 Q50 68 62 58" fill="none" stroke="var(--color-text)" strokeWidth="5" strokeLinecap="round" />
                <circle cx="28" cy="56" r="5" fill="oklch(0.85 0.09 20)" />
                <circle cx="72" cy="56" r="5" fill="oklch(0.85 0.09 20)" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="62" height="62" viewBox="0 0 100 100">
                  <path d="M50 10 C74 10 90 26 90 48 C90 70 74 84 50 84 C44 84 38 83 33 81 L16 90 L20 74 C13 67 10 58 10 48 C10 26 26 10 50 10 Z" fill="var(--color-neutral-100)" stroke="var(--color-text)" strokeWidth="6" strokeLinejoin="round" />
                  <circle cx="38" cy="44" r="6" fill="var(--color-text)" />
                  <circle cx="62" cy="44" r="6" fill="var(--color-text)" />
                  <path d="M38 58 Q50 68 62 58" fill="none" stroke="var(--color-text)" strokeWidth="6" strokeLinecap="round" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
                <svg width="42" height="42" viewBox="0 0 100 100">
                  <path d="M50 10 C74 10 90 26 90 48 C90 70 74 84 50 84 C44 84 38 83 33 81 L16 90 L20 74 C13 67 10 58 10 48 C10 26 26 10 50 10 Z" fill="oklch(0.91 0.06 300)" />
                  <circle cx="38" cy="44" r="6" fill="var(--color-text)" />
                  <circle cx="62" cy="44" r="6" fill="var(--color-text)" />
                  <path d="M38 58 Q50 68 62 58" fill="none" stroke="var(--color-text)" strokeWidth="6" strokeLinecap="round" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "40px", color: "var(--color-neutral-100)" }}>billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A smiling chat bubble. A friend who helps with the bill.</p>
          </div>
          <div id="3b" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Plus coin</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>3b</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center", gap: "22px" }}>
              <svg width="160" height="160" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="44" fill="var(--color-accent)" />
                <circle cx="50" cy="50" r="35" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2.5" />
                <rect x="42" y="26" width="16" height="48" rx="5" fill="var(--color-neutral-100)" />
                <rect x="26" y="42" width="48" height="16" rx="5" fill="var(--color-neutral-100)" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>Billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="60" height="60" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="44" fill="var(--color-accent)" />
                  <rect x="42" y="26" width="16" height="48" rx="5" fill="var(--color-neutral-100)" />
                  <rect x="26" y="42" width="48" height="16" rx="5" fill="var(--color-neutral-100)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
                <svg width="40" height="40" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="44" fill="var(--color-accent-300)" />
                  <rect x="42" y="26" width="16" height="48" rx="5" fill="var(--color-text)" />
                  <rect x="26" y="42" width="48" height="16" rx="5" fill="var(--color-text)" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "40px", color: "var(--color-neutral-100)" }}>Billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A medical cross on a gold coin. Health and money, together.</p>
          </div>
          <div id="3c" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Stacked</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>3c</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center", gap: "24px" }}>
              <svg width="150" height="170" viewBox="0 0 90 100">
                <rect x="6" y="64" width="78" height="26" rx="13" fill="oklch(0.91 0.05 235)" stroke="var(--color-text)" strokeWidth="4" />
                <rect x="12" y="38" width="70" height="26" rx="13" fill="oklch(0.90 0.06 50)" stroke="var(--color-text)" strokeWidth="4" />
                <rect x="4" y="12" width="74" height="26" rx="13" fill="var(--color-accent)" stroke="var(--color-text)" strokeWidth="4" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="54" height="60" viewBox="0 0 90 100">
                  <rect x="6" y="64" width="78" height="26" rx="13" fill="oklch(0.91 0.05 235)" />
                  <rect x="12" y="38" width="70" height="26" rx="13" fill="oklch(0.90 0.06 50)" />
                  <rect x="4" y="12" width="74" height="26" rx="13" fill="var(--color-accent-300)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
                <svg width="36" height="40" viewBox="0 0 90 100">
                  <rect x="6" y="64" width="78" height="26" rx="13" fill="oklch(0.91 0.05 235)" stroke="var(--color-text)" strokeWidth="5" />
                  <rect x="12" y="38" width="70" height="26" rx="13" fill="oklch(0.90 0.06 50)" stroke="var(--color-text)" strokeWidth="5" />
                  <rect x="4" y="12" width="74" height="26" rx="13" fill="var(--color-accent)" stroke="var(--color-text)" strokeWidth="5" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "40px" }}>billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Price, booking and bill stacked up like messages in one chat.</p>
          </div>
          <div id="3d" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Seal</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>3d</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="220" height="220" viewBox="0 0 100 100">
                <defs>
                  <path id="sealArc" d="M50 50 m-34 0 a34 34 0 1 1 68 0 a34 34 0 1 1 -68 0" />
                </defs>
                <circle cx="50" cy="50" r="46" fill="var(--color-neutral-100)" stroke="var(--color-text)" strokeWidth="2" />
                <circle cx="50" cy="50" r="26" fill="var(--color-text)" />
                <text fontFamily="Times New Roman, Times, serif" fontSize="7.2" fill="var(--color-text)">
                  <textPath href="#sealArc" textLength="208" lengthAdjust="spacing">MAKE EVERY CARE DOLLAR COUNT · BILLO ·</textPath>
                </text>
                <text x="50" y="60" textAnchor="middle" fontFamily="Times New Roman, Times, serif" fontStyle="italic" fontSize="30" fill="var(--color-neutral-100)">B</text>
                <circle cx="62" cy="58" r="3" fill="var(--color-accent-300)" />
              </svg>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "58px", color: "var(--color-neutral-100)" }}>
                B
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--color-accent-300)", alignSelf: "flex-end", marginBottom: "24px" }} />
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontSize: "13px", letterSpacing: ".18em" }}>VERIFIED BY BILLO</div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A round stamp with the tagline, like the seal on a checked bill.</p>
          </div>
        </div>
      </section>
      <section style={{ padding: "56px 56px 0", display: "flex", flexDirection: "column", gap: "32px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "56px", margin: "0" }}>
          More directions{" "}
          <em>— round 2</em>
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "28px" }}>
          <div id="2a" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Receipt letters</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>2a</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.91 0.05 235)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ display: "flex", alignItems: "flex-end", gap: "6px", fontFamily: "var(--font-heading)", fontSize: "150px", lineHeight: ".72", letterSpacing: "-.02em" }}>
                <span>bi</span>
                <svg width="26" height="106" viewBox="0 0 26 106">
                  <path d="M0 7 L6.5 0 L13 7 L19.5 0 L26 7 V106 H0 Z" fill="var(--color-text)" />
                </svg>
                <svg width="26" height="106" viewBox="0 0 26 106">
                  <path d="M0 7 L6.5 0 L13 7 L19.5 0 L26 7 V106 H0 Z" fill="var(--color-text)" />
                </svg>
                <svg width="66" height="66" viewBox="0 0 66 66" style={{ marginLeft: "4px" }}>
                  <circle cx="33" cy="33" r="31" fill="var(--color-accent)" />
                  <circle cx="33" cy="33" r="21" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2.5" />
                </svg>
              </div>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "flex-end", justifyContent: "center", gap: "6px", paddingBottom: "22px", boxSizing: "border-box" }}>
                <svg width="13" height="46" viewBox="0 0 26 92">
                  <path d="M0 7 L6.5 0 L13 7 L19.5 0 L26 7 V92 H0 Z" fill="var(--color-neutral-100)" />
                </svg>
                <svg width="13" height="46" viewBox="0 0 26 92">
                  <path d="M0 7 L6.5 0 L13 7 L19.5 0 L26 7 V92 H0 Z" fill="var(--color-neutral-100)" />
                </svg>
                <svg width="22" height="22" viewBox="0 0 66 66">
                  <circle cx="33" cy="33" r="31" fill="var(--color-accent-300)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "oklch(0.91 0.05 235)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontSize: "20px" }}>
                Make every care dollar{" "}
                <em style={{ marginLeft: "5px" }}>count.</em>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>The two l's are receipts and the o is a coin.</p>
          </div>
          <div id="2b" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>The thread</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>2b</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center", gap: "22px" }}>
              <svg width="160" height="160" viewBox="0 0 100 100">
                <path d="M16 52 L40 76 L84 26" fill="none" stroke="var(--color-text)" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="16" cy="52" r="10" fill="oklch(0.92 0.06 165)" stroke="var(--color-text)" strokeWidth="3.5" />
                <circle cx="40" cy="76" r="10" fill="oklch(0.91 0.06 300)" stroke="var(--color-text)" strokeWidth="3.5" />
                <circle cx="84" cy="26" r="12" fill="var(--color-accent)" stroke="var(--color-text)" strokeWidth="3.5" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>Billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="60" height="60" viewBox="0 0 100 100">
                  <path d="M16 52 L40 76 L84 26" fill="none" stroke="var(--color-neutral-100)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="16" cy="52" r="11" fill="oklch(0.92 0.06 165)" />
                  <circle cx="40" cy="76" r="11" fill="oklch(0.91 0.06 300)" />
                  <circle cx="84" cy="26" r="13" fill="var(--color-accent-300)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center", gap: "14px", fontSize: "15px" }}>
                <span>Before</span>
                <span>·</span>
                <span>During</span>
                <span>·</span>
                <span>After</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Three dots for before, during and after, joined into one check mark.</p>
          </div>
          <div id="2c" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Price tag</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>2c</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center", gap: "22px" }}>
              <svg width="170" height="170" viewBox="0 0 100 100">
                <path d="M36 14 H84 a6 6 0 0 1 6 6 V80 a6 6 0 0 1 -6 6 H36 L10 50 Z" fill="var(--color-text)" stroke="var(--color-text)" strokeWidth="6" strokeLinejoin="round" />
                <circle cx="30" cy="50" r="6" fill="oklch(0.90 0.06 50)" />
                <text x="64" y="70" textAnchor="middle" fontFamily="Times New Roman, Times, serif" fontStyle="italic" fontSize="58" fill="var(--color-neutral-100)">b</text>
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="62" height="62" viewBox="0 0 100 100">
                  <path d="M36 14 H84 a6 6 0 0 1 6 6 V80 a6 6 0 0 1 -6 6 H36 L10 50 Z" fill="var(--color-text)" stroke="var(--color-text)" strokeWidth="6" strokeLinejoin="round" />
                  <circle cx="30" cy="50" r="6" fill="oklch(0.90 0.06 50)" />
                  <text x="64" y="70" textAnchor="middle" fontFamily="Times New Roman, Times, serif" fontStyle="italic" fontSize="58" fill="var(--color-neutral-100)">b</text>
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
                <svg width="42" height="42" viewBox="0 0 100 100">
                  <path d="M36 14 H84 a6 6 0 0 1 6 6 V80 a6 6 0 0 1 -6 6 H36 L10 50 Z" fill="var(--color-accent-300)" stroke="var(--color-accent-300)" strokeWidth="6" strokeLinejoin="round" />
                  <circle cx="30" cy="50" r="6" fill="var(--color-text)" />
                  <text x="64" y="70" textAnchor="middle" fontFamily="Times New Roman, Times, serif" fontStyle="italic" fontSize="58" fill="var(--color-text)">b</text>
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "40px", color: "var(--color-neutral-100)" }}>billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A price tag: see the price before you go.</p>
          </div>
          <div id="2d" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Care coin</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>2d</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center", gap: "22px" }}>
              <svg width="160" height="160" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="44" fill="var(--color-accent)" />
                <circle cx="50" cy="50" r="35" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2.5" />
                <path d="M50 72 C 30 58, 24 46, 30 37 C 36 29, 46 31, 50 39 C 54 31, 64 29, 70 37 C 76 46, 70 58, 50 72 Z" fill="var(--color-neutral-100)" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>Billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="60" height="60" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="44" fill="var(--color-accent-300)" />
                  <path d="M50 72 C 30 58, 24 46, 30 37 C 36 29, 46 31, 50 39 C 54 31, 64 29, 70 37 C 76 46, 70 58, 50 72 Z" fill="var(--color-text)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
                <svg width="40" height="40" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="44" fill="var(--color-accent)" />
                  <path d="M50 72 C 30 58, 24 46, 30 37 C 36 29, 46 31, 50 39 C 54 31, 64 29, 70 37 C 76 46, 70 58, 50 72 Z" fill="var(--color-neutral-100)" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "40px" }}>Billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Care plus money: a heart stamped on a coin.</p>
          </div>
        </div>
      </section>
      <section style={{ padding: "56px", display: "flex", flexDirection: "column", gap: "32px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "56px", margin: "0" }}>
          Billo logo,{" "}
          <em>four directions</em>
        </h1>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "28px" }}>
          {/* 1a */}
          <div id="1a" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Coin dot</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>1a</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ display: "flex", alignItems: "baseline", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "132px", lineHeight: "1", letterSpacing: "-.03em" }}>
                Billo
                <svg width="40" height="40" viewBox="0 0 40 40" style={{ marginLeft: "4px" }}>
                  <circle cx="20" cy="20" r="18" fill="var(--color-accent)" />
                  <circle cx="20" cy="20" r="12" fill="none" stroke="var(--color-neutral-100)" strokeWidth="2" />
                </svg>
              </div>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "62px", color: "var(--color-neutral-100)" }}>
                B
                <svg width="14" height="14" viewBox="0 0 40 40" style={{ alignSelf: "flex-end", marginBottom: "22px" }}>
                  <circle cx="20" cy="20" r="18" fill="var(--color-accent)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "44px", color: "var(--color-neutral-100)" }}>
                Billo
                <svg width="13" height="13" viewBox="0 0 40 40" style={{ marginLeft: "2px", alignSelf: "center", marginTop: "18px" }}>
                  <circle cx="20" cy="20" r="18" fill="var(--color-accent-300)" />
                </svg>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>The full stop is a coin: every dollar, accounted for.</p>
          </div>
          {/* 1b */}
          <div id="1b" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Chat b</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>1b</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center", gap: "22px" }}>
              <svg width="170" height="170" viewBox="0 0 100 100">
                <rect x="14" y="6" width="17" height="74" rx="8.5" fill="var(--color-text)" />
                <circle cx="57" cy="60" r="25" fill="none" stroke="var(--color-text)" strokeWidth="17" />
                <path d="M14 70 L14 96 L40 86 Z" fill="var(--color-text)" />
                <circle cx="57" cy="60" r="8" fill="var(--color-accent)" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="58" height="58" viewBox="0 0 100 100">
                  <rect x="14" y="6" width="17" height="74" rx="8.5" fill="var(--color-text)" />
                  <circle cx="57" cy="60" r="25" fill="none" stroke="var(--color-text)" strokeWidth="17" />
                  <path d="M14 70 L14 96 L40 86 Z" fill="var(--color-text)" />
                  <circle cx="57" cy="60" r="8" fill="var(--color-accent)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
                <svg width="42" height="42" viewBox="0 0 100 100">
                  <rect x="14" y="6" width="17" height="74" rx="8.5" fill="var(--color-neutral-100)" />
                  <circle cx="57" cy="60" r="25" fill="none" stroke="var(--color-neutral-100)" strokeWidth="17" />
                  <path d="M14 70 L14 96 L40 86 Z" fill="var(--color-neutral-100)" />
                  <circle cx="57" cy="60" r="8" fill="var(--color-accent-300)" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "40px", color: "var(--color-neutral-100)" }}>billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>A "b" that is also a chat bubble, with a coin inside.</p>
          </div>
          {/* 1c */}
          <div id="1c" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>Receipt bubble</span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>1c</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center", gap: "22px" }}>
              <svg width="170" height="170" viewBox="0 0 100 100">
                <path d="M14 18 a8 8 0 0 1 8-8 H78 a8 8 0 0 1 8 8 V70 L80 76 L74 70 L68 76 L62 70 L56 76 L50 70 L44 76 L38 70 L32 76 L28 72 L28 92 L14 76 Z" fill="var(--color-neutral-100)" stroke="var(--color-text)" strokeWidth="5" strokeLinejoin="round" />
                <path d="M32 42 L45 55 L68 30" fill="none" stroke="var(--color-text)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>Billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "oklch(0.92 0.06 165)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="60" height="60" viewBox="0 0 100 100">
                  <path d="M14 18 a8 8 0 0 1 8-8 H78 a8 8 0 0 1 8 8 V70 L80 76 L74 70 L68 76 L62 70 L56 76 L50 70 L44 76 L38 70 L32 76 L28 72 L28 92 L14 76 Z" fill="var(--color-neutral-100)" stroke="var(--color-text)" strokeWidth="5" strokeLinejoin="round" />
                  <path d="M32 42 L45 55 L68 30" fill="none" stroke="var(--color-text)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
                <svg width="44" height="44" viewBox="0 0 100 100">
                  <path d="M14 18 a8 8 0 0 1 8-8 H78 a8 8 0 0 1 8 8 V70 L80 76 L74 70 L68 76 L62 70 L56 76 L50 70 L44 76 L38 70 L32 76 L28 72 L28 92 L14 76 Z" fill="oklch(0.92 0.06 165)" />
                  <path d="M32 42 L45 55 L68 30" fill="none" stroke="var(--color-text)" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "40px", color: "var(--color-neutral-100)" }}>Billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Chat on top, torn receipt below. The check means the bill is matched.</p>
          </div>
          {/* 1d */}
          <div id="1d" style={{ width: "560px", background: "var(--color-neutral-100)", borderRadius: "32px", padding: "28px", display: "flex", flexDirection: "column", gap: "20px", boxShadow: "var(--shadow-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "24px", fontFamily: "var(--font-heading)" }}>
                @ coin{" "}
                <span style={{ fontSize: "14px", background: "oklch(0.92 0.06 165)", borderRadius: "99px", padding: "3px 10px", marginLeft: "6px" }}>Chosen</span>
              </span>
              <span style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px 12px", fontSize: "14px" }}>1d</span>
            </div>
            <div style={{ height: "300px", borderRadius: "24px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center", gap: "14px" }}>
              <svg width="150" height="150" viewBox="0 0 100 100">
                <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="10" strokeLinecap="round" />
                <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
              </svg>
              <span style={{ fontFamily: "var(--font-heading)", fontSize: "88px", lineHeight: "1", letterSpacing: "-.02em" }}>billo</span>
            </div>
            <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "88px", height: "88px", borderRadius: "22px", background: "oklch(0.90 0.06 50)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="58" height="58" viewBox="0 0 100 100">
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-text)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent)" />
                </svg>
              </div>
              <div style={{ flex: "1", height: "88px", borderRadius: "22px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                <svg width="40" height="40" viewBox="0 0 100 100">
                  <path d="M86 50 A36 36 0 1 0 68 81" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" />
                  <path d="M64 32 V56 Q64 68 75 68 Q86 68 86 50" fill="none" stroke="var(--color-neutral-100)" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="47" cy="50" r="14" fill="var(--color-accent-300)" />
                </svg>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "40px", color: "var(--color-neutral-100)" }}>billo</span>
              </div>
            </div>
            <p style={{ margin: "0", fontSize: "16px", lineHeight: "1.4" }}>Built on "@billo", the way people call it. A coin sits in the center.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
