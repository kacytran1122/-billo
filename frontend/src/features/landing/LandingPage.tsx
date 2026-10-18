"use client";

/**
 * Billo landing page (migrated from "Billo 1.html").
 * Sticky pill navigation with scroll-spy, a "where do you want to chat?"
 * chooser dialog, two hero phone mockups and scroll-reveal animations.
 */
import { Fragment, useCallback, useEffect, useRef, useState, type MouseEvent } from "react";
import Link from "next/link";
import { BilloLogo } from "@/components/BilloLogo";
import { BilloWord } from "@/components/BilloWord";
import { LandingIntro } from "@/components/loading/LandingIntro";
import { QRCells } from "@/components/QRCells";
import { makeQR } from "@/lib/qr";
import { ChannelConnect, type ConnectChannel } from "@/features/connect/ChannelConnect";
import { FeatureSimulation, type FeatureStep } from "@/features/simulation/FeatureSimulation";
import hv from "./LandingPage.module.css";

export type HeroPhones = "Both" | "ASI:One only" | "WhatsApp only";

type SectionId = "top" | "case" | "features" | "faq";

const SECTIONS: ReadonlyArray<readonly [SectionId, string]> = [
  ["top", "Home"],
  ["case", "How it works"],
  ["features", "Features"],
  ["faq", "FAQ"],
];

const QR = makeQR("BILLO-4821");

const REVEAL_SELECTORS = [
  "#top h1", "#top p", "#top h1 ~ div", "section h2", "section h2 + p",
  "#case > div > *", "#features > div > div", "#pages a", "#faq details", "footer",
];

/** Fade/slide elements in as they scroll into view (skipped for reduced motion). */
function useScrollReveal() {
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    if (!("IntersectionObserver" in window)) return;

    const els = [...new Set(REVEAL_SELECTORS.flatMap((s) => [...document.querySelectorAll<HTMLElement>(s)]))];
    const vh = window.innerHeight;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (!en.isIntersecting) return;
          const el = en.target as HTMLElement;
          el.style.opacity = "1";
          el.style.translate = "0 0";
          el.style.scale = "1";
          io.unobserve(el);
          setTimeout(() => {
            el.style.transition = "";
            el.style.willChange = "";
          }, 1200);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 },
    );

    els.forEach((el) => {
      if (el.getBoundingClientRect().top < vh * 0.9 && !el.closest("#features,#case,#pages,#faq")) return;
      const sibs = el.parentElement ? [...el.parentElement.children] : [];
      const delay = Math.min(Math.max(0, sibs.indexOf(el)), 7) * 70;
      const ease = "cubic-bezier(.2,.7,.2,1)";
      el.style.opacity = "0";
      el.style.translate = "0 28px";
      el.style.scale = ".985";
      el.style.willChange = "opacity, translate";
      el.style.transition = `opacity .7s ${ease} ${delay}ms, translate .8s ${ease} ${delay}ms, scale .8s ${ease} ${delay}ms`;
      io.observe(el);
    });

    return () => {
      io.disconnect();
      els.forEach((el) => {
        el.style.opacity = el.style.translate = el.style.scale = el.style.transition = el.style.willChange = "";
      });
    };
  }, []);
}

export default function LandingPage({ heroPhones = "Both" }: { heroPhones?: HeroPhones }) {
  const [menu, setMenu] = useState(false);
  const [active, setActive] = useState<SectionId>("top");
  const [chooser, setChooser] = useState(false);
  const [connectChannel, setConnectChannel] = useState<ConnectChannel>("asi");
  const [featureStep, setFeatureStep] = useState<FeatureStep>("prices");
  const activeRef = useRef<SectionId>("top");
  const progressRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    let frame = 0;
    const updateActiveSection = () => {
      const marker = Math.min(window.innerHeight * 0.38, 220);
      const scrollRange = document.documentElement.scrollHeight - window.innerHeight;
      const progress = scrollRange > 0 ? Math.min(1, Math.max(0, window.scrollY / scrollRange)) : 0;
      if (progressRef.current) progressRef.current.style.transform = `scaleX(${progress})`;
      let a: SectionId = "top";
      for (const [id] of SECTIONS.slice(1)) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= marker) a = id;
      }
      if (a !== activeRef.current) {
        activeRef.current = a;
        setActive(a);
        try {
          history.replaceState(null, "", a === "top" ? location.pathname + location.search : "#" + a);
        } catch {}
      }
      frame = 0;
    };
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(updateActiveSection);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    updateActiveSection();
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  useScrollReveal();

  const jump = useCallback(
    (id: SectionId) => (ev?: MouseEvent) => {
      ev?.preventDefault();
      const el = document.getElementById(id);
      if (el) {
        window.scrollTo({ top: id === "top" ? 0 : el.getBoundingClientRect().top + window.scrollY - 76, behavior: "smooth" });
      }
      setMenu(false);
    },
    [],
  );

  const menuOpen = menu;
  const menuClosed = !menuOpen;
  const showMenu = menuOpen;
  const toggleMenu = () => setMenu((m) => !m);
  const goTop = jump("top");
  const chooserOpen = chooser;
  const openChooser = (channel: ConnectChannel = "asi") => {
    setConnectChannel(channel);
    setChooser(true);
    setMenu(false);
  };
  const closeChooser = () => setChooser(false);
  const links = SECTIONS.map(([id, label]) => ({
    label,
    href: "#" + id,
    go: jump(id),
    active: active === id,
    inactive: active !== id,
  }));
  const activeLabel = SECTIONS.find(([id]) => id === active)?.[1] ?? "Home";
  useEffect(() => {
    if (window.location.hash === "#connect") openChooser("whatsapp");
  }, []);
  const showAsi = heroPhones !== "WhatsApp only";
  const showIMessage = heroPhones !== "ASI:One only";
  const qr = QR;

  return (
    <div className="page page--neutral-100">
      <LandingIntro />
      <div className={hv.headerSpacer} />
      <header style={{ position: "fixed", top: "0", left: "0", right: "0", zIndex: "50", background: "color-mix(in oklch, oklch(0.91 0.06 300) 88%, transparent)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)", borderBottom: "1px solid oklch(0.84 0.07 300)" }}>
        <div className={hv.headerInner} style={{ maxWidth: "1240px", margin: "0 auto", padding: "12px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          <a href="#top" onClick={goTop} aria-label="Billo" style={{ color: "var(--color-text)", textDecoration: "none" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontFamily: "var(--font-heading)", fontSize: "32px", fontWeight: "400", fontStyle: "normal", lineHeight: "1", letterSpacing: "-.02em" }}>
              <BilloLogo size={34} />
              <span style={{ display: "inline-flex", alignItems: "baseline" }}>billo</span>
            </span>
          </a>
          <span className={hv.mobileSectionLabel} aria-live="polite">{activeLabel}</span>
          <div className={hv.desktopNavigation}>
              <nav aria-label="Main" style={{ display: "flex", gap: "4px", alignItems: "center", fontSize: "15px", background: "var(--color-neutral-100)", borderRadius: "99px", padding: "4px", boxShadow: "var(--shadow-sm)" }}>
                {links.map((l, lIndex) => (
                  <Fragment key={lIndex}>
                    {l.active && (
                      <a href={l.href} onClick={l.go} aria-current="true" style={{ display: "flex", alignItems: "center", minHeight: "40px", padding: "0 16px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", textDecoration: "none" }}>{l.label}</a>
                    )}
                    {l.inactive && (
                      <a className={hv.hover1} href={l.href} onClick={l.go} style={{ display: "flex", alignItems: "center", minHeight: "40px", padding: "0 16px", borderRadius: "99px", color: "var(--color-text)", textDecoration: "none" }}>{l.label}</a>
                    )}
                  </Fragment>
                ))}
              </nav>
              <button className={hv.hover2} onClick={() => openChooser("asi")} style={{ display: "flex", alignItems: "center", gap: "8px", minHeight: "44px", padding: "0 20px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", border: "0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "15px" }}>
                Get started{" "}
                <span>→</span>
              </button>
          </div>
          <button className={`${hv.mobileMenuButton} ${hv.hover3}`} onClick={toggleMenu} aria-label="Menu" aria-expanded={menuOpen} style={{ width: "46px", height: "46px", borderRadius: "50%", border: "1px solid var(--color-divider)", background: "var(--color-neutral-100)", color: "var(--color-text)", cursor: "pointer", alignItems: "center", justifyContent: "center", flex: "none" }}>
              {menuClosed && (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M4 7h16M4 12h16M4 17h16" />
                </svg>
              )}
              {menuOpen && (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              )}
          </button>
        </div>
        {showMenu && (
          <nav className={hv.mobileNavigation} aria-label="Main" style={{ padding: "4px 16px 16px", flexDirection: "column", gap: "6px", fontSize: "19px" }}>
            {links.map((l, lIndex) => (
              <Fragment key={lIndex}>
                {l.active && (
                  <a href={l.href} onClick={l.go} aria-current="true" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", minHeight: "54px", padding: "0 20px", borderRadius: "18px", background: "var(--color-text)", color: "var(--color-neutral-100)", textDecoration: "none" }}>
                    <span>{l.label}</span>
                    <span>→</span>
                  </a>
                )}
                {l.inactive && (
                  <a href={l.href} onClick={l.go} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", minHeight: "54px", padding: "0 20px", borderRadius: "18px", background: "var(--color-neutral-200)", color: "var(--color-text)", textDecoration: "none" }}>
                    <span>{l.label}</span>
                    <span>→</span>
                  </a>
                )}
              </Fragment>
            ))}
            <button onClick={() => openChooser("asi")} style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "54px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", border: "0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "17px", marginTop: "4px" }}>Get started →</button>
          </nav>
        )}
        <div className={hv.scrollProgress} aria-hidden="true">
          <span ref={progressRef} />
        </div>
      </header>
      <ChannelConnect open={chooserOpen} initialChannel={connectChannel} onClose={closeChooser} />
      <div style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", fontSize: "13px", textAlign: "center", padding: "8px 16px" }}>
        Emergency? Call{" "}
        <a href="tel:911" style={{ color: "var(--color-accent-300)" }}>911</a>
        . Billo doesn't handle emergencies.
      </div>
      <section id="top" className={hv.hero} style={{ position: "relative", overflow: "hidden", scrollMarginTop: "80px" }}>
        <div style={{ position: "absolute", width: "520px", height: "520px", borderRadius: "50%", background: "oklch(0.92 0.06 165)", left: "-160px", top: "180px" }} />
        <div style={{ position: "absolute", width: "440px", height: "440px", borderRadius: "50%", background: "oklch(0.91 0.06 300)", right: "-120px", top: "60px" }} />
        <div style={{ position: "absolute", width: "300px", height: "300px", borderRadius: "50%", background: "oklch(0.94 0.08 95)", left: "48%", top: "520px" }} />
        <div className={hv.heroInner} style={{ position: "relative", maxWidth: "1240px", margin: "0 auto", padding: "48px 24px 96px", textAlign: "center" }}>
          <div className={hv.heroEyebrow} style={{ display: "inline-flex", gap: "8px", alignItems: "center", background: "var(--color-neutral-100)", border: "1px solid var(--color-divider)", borderRadius: "99px", padding: "6px 14px 6px 8px", fontSize: "13px" }}>
            <span style={{ background: "oklch(0.90 0.06 50)", borderRadius: "99px", padding: "2px 10px" }}>New</span>
            Now in ASI:One{" "}
            &amp;
            {" "}WhatsApp
          </div>
          <h1 className={hv.heroTitle} style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(56px,9vw,124px)", lineHeight: ".9", letterSpacing: "-.025em", margin: "26px auto 0", maxWidth: "980px", textWrap: "balance" }}>
            Make every care dollar{" "}
            <em style={{ color: "var(--color-accent-700)" }}>count.</em>
          </h1>
          <p className={hv.heroSubtitle} style={{ fontSize: "19px", lineHeight: "1.5", margin: "22px auto 0", maxWidth: "460px", color: "var(--color-neutral-800)" }}>Compare prices before. Check the bill after. All in one chat.</p>
          <div className={hv.heroActions} style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap", marginTop: "32px" }}>
            <button onClick={() => openChooser("asi")} style={{ display: "inline-flex", alignItems: "center", gap: "10px", minHeight: "54px", padding: "0 26px", borderRadius: "99px", border: "0", background: "var(--color-text)", color: "var(--color-neutral-100)", fontFamily: "var(--font-body)", cursor: "pointer", fontSize: "16px" }}>
              <span style={{ width: "22px", height: "22px", borderRadius: "6px", border: "1.5px solid var(--color-accent-300)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "14px", color: "var(--color-accent-300)" }}>A</span>
              Open in ASI:One
            </button>
            {" "}
            <button onClick={() => openChooser("whatsapp")} style={{ display: "inline-flex", alignItems: "center", gap: "10px", minHeight: "54px", padding: "0 26px", borderRadius: "99px", background: "var(--color-neutral-100)", border: "1px solid var(--color-text)", color: "var(--color-text)", fontFamily: "var(--font-body)", cursor: "pointer", fontSize: "16px" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="oklch(0.6 0.17 255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
              </svg>
              Text on WhatsApp
            </button>
          </div>
          <div className={hv.heroFeatureStrip} aria-label="Billo features">
            <span>Emergency rules first</span>
            <span>Real care prices</span>
            <span>Bill &amp; receipt OCR</span>
            <span>Benefit paths</span>
          </div>
          <div className={hv.heroPhones} data-single={heroPhones === "Both" ? "false" : "true"} style={{ position: "relative", display: "flex", justifyContent: "center", alignItems: "flex-start", gap: "40px", flexWrap: "wrap", marginTop: "72px" }}>
            {showAsi && (
              <div className={hv.phoneAsi} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "18px", transform: "rotate(-3deg)" }}>
                <div className={hv.phoneFrame} style={{ width: "290px", height: "600px", borderRadius: "48px", background: "var(--color-text)", padding: "10px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box" }}>
                  <div style={{ width: "100%", height: "100%", borderRadius: "38px", background: "var(--color-neutral-100)", overflow: "hidden", display: "flex", flexDirection: "column", textAlign: "left" }}>
                    <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 6px" }}>
                      <div style={{ width: "84px", height: "22px", borderRadius: "12px", background: "var(--color-text)" }} />
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "6px 16px 12px", borderBottom: "1px solid oklch(0.84 0.07 300)" }}>
                      <div style={{ width: "32px", height: "32px", borderRadius: "10px", background: "oklch(0.94 0.08 95)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <BilloLogo size={22} />
                      </div>
                      <div>
                        <div style={{ fontFamily: "var(--font-heading)", fontWeight: "600", fontSize: "17px", lineHeight: "1.1" }}>Billo</div>
                        <div style={{ fontSize: "10.5px", color: "var(--color-neutral-700)" }}>ASI:One agent</div>
                      </div>
                    </div>
                    <div style={{ flex: "1", minHeight: "0", overflow: "hidden", padding: "14px 12px", display: "flex", flexDirection: "column", gap: "9px", fontSize: "12.5px", lineHeight: "1.4" }}>
                      <div style={{ flexShrink: "0", alignSelf: "flex-end", maxWidth: "75%", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "8px 12px", borderRadius: "16px 16px 4px 16px" }}>
                        <BilloWord />
                        {" "}twisted my knee. Swollen, but I can walk.
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-start", display: "inline-flex", gap: "6px", alignItems: "center", background: "oklch(0.92 0.06 165)", padding: "5px 10px", borderRadius: "99px", fontSize: "11px" }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                        No emergency signs
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-start", width: "92%", background: "var(--color-bg)", borderRadius: "14px", overflow: "hidden", border: "1px solid var(--color-divider)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", background: "oklch(0.94 0.08 95)" }}>
                          <span style={{ fontWeight: "600" }}>Westwood Urgent</span>
                          <span style={{ fontFamily: "var(--font-heading)", fontSize: "20px", fontVariantNumeric: "tabular-nums" }}>$240</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", borderTop: "1px solid var(--color-divider)" }}>
                          <span>Campus Health</span>
                          <span style={{ fontFamily: "var(--font-heading)", fontSize: "20px", fontVariantNumeric: "tabular-nums" }}>$180</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 12px", borderTop: "1px solid var(--color-divider)" }}>
                          <span>Santa Monica ER</span>
                          <span style={{ fontFamily: "var(--font-heading)", fontSize: "20px", fontVariantNumeric: "tabular-nums" }}>$1,800</span>
                        </div>
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-end", maxWidth: "75%", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "8px 12px", borderRadius: "16px 16px 4px 16px" }}>
                        <BilloWord />
                        {" "}book Westwood
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-start", maxWidth: "85%", background: "var(--color-bg)", border: "1px solid var(--color-divider)", padding: "8px 12px", borderRadius: "16px 16px 16px 4px" }}>
                        Booked. Expected price:{" "}
                        <strong style={{ fontWeight: "600" }}>$240</strong>
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-start", display: "flex", gap: "6px" }}>
                        <span style={{ background: "oklch(0.91 0.05 235)", padding: "5px 10px", borderRadius: "99px", fontSize: "11px" }}>Add to calendar</span>
                        {" "}
                        <span style={{ background: "oklch(0.90 0.06 50)", padding: "5px 10px", borderRadius: "99px", fontSize: "11px" }}>Directions</span>
                      </div>
                    </div>
                  </div>
                </div>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontStyle: "italic" }}>Before care · ASI:One</span>
              </div>
            )}
            {showIMessage && (
              <div className={hv.phoneIMessage} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "18px", transform: "rotate(3deg) translateY(36px)" }}>
                <div className={hv.phoneFrame} style={{ width: "290px", height: "600px", borderRadius: "48px", background: "var(--color-text)", padding: "10px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box" }}>
                  <div style={{ width: "100%", height: "100%", borderRadius: "38px", background: "#ffffff", overflow: "hidden", display: "flex", flexDirection: "column", textAlign: "left", fontFamily: "var(--font-body)" }}>
                    <div style={{ display: "flex", justifyContent: "center", padding: "10px 0 6px" }}>
                      <div style={{ width: "84px", height: "22px", borderRadius: "12px", background: "var(--color-text)" }} />
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "3px", padding: "4px 0 10px", borderBottom: "1px solid var(--color-neutral-200)", background: "var(--color-neutral-100)" }}>
                      <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "oklch(0.91 0.06 300)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <BilloLogo size={27} />
                      </div>
                      <span style={{ fontSize: "11px" }}>Billo</span>
                    </div>
                    <div style={{ flex: "1", minHeight: "0", overflow: "hidden", padding: "12px 12px", display: "flex", flexDirection: "column", gap: "6px", fontSize: "13px", lineHeight: "1.35" }}>
                      <div style={{ alignSelf: "center", fontSize: "10px", color: "var(--color-neutral-600)" }}>WhatsApp · Today 4:12 PM</div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-end", maxWidth: "70%", background: "oklch(0.6 0.17 255)", color: "#fff", padding: "8px 12px", borderRadius: "18px" }}>
                        <BilloWord />
                        {" "}the bill
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-end", width: "132px", background: "var(--color-neutral-100)", border: "1px solid var(--color-neutral-300)", borderRadius: "14px", padding: "10px", transform: "rotate(2deg)" }}>
                        <div style={{ fontSize: "9px", fontWeight: "600", letterSpacing: ".06em" }}>WESTWOOD URGENT CARE</div>
                        <div style={{ height: "3px", background: "var(--color-neutral-300)", borderRadius: "2px", marginTop: "8px", width: "90%" }} />
                        <div style={{ height: "3px", background: "var(--color-neutral-300)", borderRadius: "2px", marginTop: "5px", width: "70%" }} />
                        <div style={{ height: "3px", background: "var(--color-neutral-300)", borderRadius: "2px", marginTop: "5px", width: "80%" }} />
                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "10px", fontWeight: "600" }}>
                          <span>TOTAL</span>
                          <span>$360.00</span>
                        </div>
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-start", maxWidth: "82%", background: "#e9e9eb", color: "#000", padding: "8px 12px", borderRadius: "18px" }}>Matches Westwood. $240 expected + $120 X-ray you logged.</div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-start", background: "oklch(0.92 0.06 165)", color: "#000", padding: "10px 12px", borderRadius: "18px", width: "72%" }}>
                        <div style={{ fontSize: "10px", letterSpacing: ".06em", textTransform: "uppercase" }}>Verified record</div>
                        <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1", marginTop: "2px" }}>$360.00</div>
                      </div>
                      <div style={{ flexShrink: "0", alignSelf: "flex-end", maxWidth: "70%", background: "oklch(0.6 0.17 255)", color: "#fff", padding: "8px 12px", borderRadius: "18px" }}>Perfect, thank you!</div>
                    </div>
                    <div style={{ padding: "8px 12px 16px", display: "flex", gap: "8px", alignItems: "center" }}>
                      <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: "var(--color-neutral-200)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "18px", color: "var(--color-neutral-700)" }}>+</div>
                      <div style={{ flex: "1", border: "1px solid var(--color-neutral-300)", borderRadius: "18px", padding: "7px 12px", fontSize: "12px", color: "var(--color-neutral-600)" }}>WhatsApp</div>
                    </div>
                  </div>
                </div>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontStyle: "italic" }}>After care · WhatsApp</span>
              </div>
            )}
            <div className={hv.heroBadge} style={{ position: "absolute", left: "calc(50% - 420px)", top: "90px", background: "oklch(0.90 0.06 50)", borderRadius: "18px", padding: "12px 18px", boxShadow: "var(--shadow-md)", transform: "rotate(-8deg)", textAlign: "left" }}>
              <div style={{ fontSize: "11px", letterSpacing: ".08em", textTransform: "uppercase" }}>Expected</div>
              <div style={{ fontFamily: "var(--font-heading)", fontSize: "38px", lineHeight: "1", fontVariantNumeric: "tabular-nums" }}>$240</div>
            </div>
            <div className={hv.heroBadge} style={{ position: "absolute", right: "calc(50% - 430px)", top: "300px", background: "oklch(0.94 0.08 95)", borderRadius: "99px", padding: "10px 18px", boxShadow: "var(--shadow-md)", transform: "rotate(6deg)", fontSize: "14px", display: "flex", gap: "8px", alignItems: "center" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
              Bill matches
            </div>
            <div className={hv.heroBadge} style={{ position: "absolute", left: "calc(50% - 400px)", top: "600px", background: "oklch(0.91 0.05 235)", borderRadius: "99px", padding: "10px 18px", boxShadow: "var(--shadow-md)", transform: "rotate(4deg)", fontSize: "14px" }}>3 prices nearby</div>
          </div>
        </div>
      </section>
      <section id="case" className={`${hv.balancedSection} ${hv.caseSection}`} style={{ scrollMarginTop: "80px", background: "oklch(0.91 0.05 235)", borderRadius: "48px", maxWidth: "1400px", margin: "110px auto 0", padding: "96px 24px", boxSizing: "border-box" }}>
        <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(44px,6vw,76px)", lineHeight: ".95", margin: "0", textAlign: "center", letterSpacing: "-.015em" }}>
          Start in ASI:One.{" "}
          <em>Continue in WhatsApp.</em>
        </h2>
        <p style={{ fontSize: "18px", lineHeight: "1.5", margin: "20px auto 0", maxWidth: "520px", textAlign: "center", color: "var(--color-neutral-800)" }}>Scan your Billo code once. Your case follows you.</p>
        <div className={hv.caseFlow} style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: "20px", marginTop: "56px" }}>
          <div style={{ flex: "1 1 240px", maxWidth: "300px", background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "28px", padding: "26px", display: "flex", flexDirection: "column", gap: "16px", minHeight: "220px", boxSizing: "border-box" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
              <span style={{ width: "24px", height: "24px", borderRadius: "7px", border: "1.5px solid var(--color-accent-300)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", color: "var(--color-accent-300)" }}>A</span>
              ASI:One
            </span>
            <div style={{ marginTop: "auto", alignSelf: "flex-end", background: "var(--color-neutral-100)", color: "var(--color-text)", padding: "9px 14px", borderRadius: "16px 16px 4px 16px", fontSize: "14px" }}>
              <BilloWord />
              {" "}book Westwood
            </div>
            <div style={{ alignSelf: "flex-start", background: "oklch(0.90 0.06 50)", color: "var(--color-text)", padding: "9px 14px", borderRadius: "16px 16px 16px 4px", fontSize: "14px" }}>Booked · expected $240</div>
          </div>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
          <div style={{ flex: "0 0 auto", background: "oklch(0.94 0.08 95)", borderRadius: "28px", padding: "22px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "150px", height: "150px", padding: "10px", background: "#fff", borderRadius: "18px", boxSizing: "border-box", display: "grid", gridTemplateColumns: "repeat(21,1fr)", gap: "0", boxShadow: "var(--shadow-md)" }}>
              <QRCells cells={qr} />
            </div>
            <span style={{ fontFamily: "var(--font-heading)", fontSize: "26px", letterSpacing: ".06em", fontVariantNumeric: "tabular-nums" }}>BILLO-4821</span>
            {" "}
            <span style={{ fontSize: "12px" }}>Scan or tap to link</span>
          </div>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
          <div style={{ flex: "1 1 240px", maxWidth: "300px", background: "#fff", border: "1px solid var(--color-neutral-300)", borderRadius: "28px", padding: "26px", display: "flex", flexDirection: "column", gap: "10px", minHeight: "220px", boxSizing: "border-box" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="oklch(0.6 0.17 255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
              </svg>
              WhatsApp
            </span>
            <div style={{ marginTop: "auto", alignSelf: "flex-end", background: "oklch(0.6 0.17 255)", color: "#fff", padding: "9px 14px", borderRadius: "18px", fontSize: "14px" }}>
              <BilloWord />
              {" "}BILLO-4821
            </div>
            <div style={{ alignSelf: "flex-start", background: "#e9e9eb", color: "#000", padding: "9px 14px", borderRadius: "18px", fontSize: "14px" }}>Linked to your Westwood visit.</div>
          </div>
        </div>
        <div style={{ maxWidth: "860px", margin: "40px auto 0", border: "1.5px solid var(--color-text)", borderRadius: "28px", padding: "22px 24px", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "center", gap: "10px 12px" }}>
          <span style={{ fontFamily: "var(--font-heading)", fontSize: "24px", fontStyle: "italic", marginRight: "8px" }}>One shared case record</span>
          {" "}
          <span style={{ background: "oklch(0.90 0.06 50)", borderRadius: "99px", padding: "8px 16px", fontSize: "14px" }}>Booking</span>
          {" "}
          <span style={{ background: "oklch(0.94 0.08 95)", borderRadius: "99px", padding: "8px 16px", fontSize: "14px" }}>Expected prices</span>
          {" "}
          <span style={{ background: "oklch(0.91 0.05 235)", borderRadius: "99px", padding: "8px 16px", fontSize: "14px" }}>Documents</span>
          {" "}
          <span style={{ background: "oklch(0.91 0.06 300)", borderRadius: "99px", padding: "8px 16px", fontSize: "14px" }}>Benefits</span>
          {" "}
          <span style={{ background: "oklch(0.92 0.06 165)", borderRadius: "99px", padding: "8px 16px", fontSize: "14px" }}>Status</span>
        </div>
      </section>
      <section id="features" className={hv.balancedSection} style={{ scrollMarginTop: "80px", maxWidth: "1240px", margin: "0 auto", padding: "110px 24px 40px" }}>
        <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(44px,6vw,76px)", lineHeight: ".95", margin: "0", textAlign: "center", letterSpacing: "-.015em" }}>
          All you need is{" "}
          <BilloWord />
          .
        </h2>
        <FeatureSimulation step={featureStep} onStepChange={setFeatureStep} />
      </section>
      <section id="pages" className={hv.balancedSection} style={{ scrollMarginTop: "80px", padding: "110px 24px 120px" }}>
        <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(44px,6vw,76px)", lineHeight: ".95", margin: "0", textAlign: "center", letterSpacing: "-.015em" }}>
          Before, during,{" "}
          <em>after.</em>
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", margin: "56px auto 0", maxWidth: "820px" }}>
          <Link className={hv.hover4} href="/journey/booked" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", background: "oklch(0.90 0.06 50)", borderRadius: "36px", padding: "30px 40px", color: "var(--color-text)", textDecoration: "none", fontSize: "clamp(20px,2.4vw,28px)" }}>
            <span>Just booked</span>
            <span style={{ fontSize: "1.2em" }}>→</span>
          </Link>
          {" "}
          <Link className={hv.hover4} href="/journey/during" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", background: "oklch(0.91 0.06 300)", borderRadius: "36px", padding: "30px 40px", color: "var(--color-text)", textDecoration: "none", fontSize: "clamp(20px,2.4vw,28px)" }}>
            <span>During the visit</span>
            <span style={{ fontSize: "1.2em" }}>→</span>
          </Link>
          {" "}
          <Link className={hv.hover4} href="/journey/verified" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", background: "oklch(0.92 0.06 165)", borderRadius: "36px", padding: "30px 40px", color: "var(--color-text)", textDecoration: "none", fontSize: "clamp(20px,2.4vw,28px)" }}>
            <span>Verified record</span>
            <span style={{ fontSize: "1.2em" }}>→</span>
          </Link>
          {" "}
          <Link className={hv.hover4} href="/journey/payment" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", background: "oklch(0.94 0.08 95)", borderRadius: "36px", padding: "30px 40px", color: "var(--color-text)", textDecoration: "none", fontSize: "clamp(20px,2.4vw,28px)" }}>
            <span>Pay, safely</span>
            <span style={{ fontSize: "1.2em" }}>→</span>
          </Link>
        </div>
      </section>
      <section id="faq" className={hv.balancedSection} style={{ scrollMarginTop: "80px", maxWidth: "900px", margin: "0 auto", padding: "110px 24px 120px" }}>
        <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(44px,6vw,76px)", lineHeight: ".95", margin: "0", textAlign: "center", letterSpacing: "-.015em" }}>
          Frequently Asked{" "}
          <em>Questions</em>
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "56px" }}>
          <details open style={{ background: "oklch(0.94 0.08 95)", borderRadius: "28px", padding: "0 28px" }}>
            <summary style={{ listStyle: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", minHeight: "76px", fontSize: "clamp(19px,2vw,24px)" }}>
              <span>Is Billo free?</span>
              <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: "22px" }}>+</span>
            </summary>
            <p style={{ margin: "0", padding: "0 0 26px", fontSize: "17px", lineHeight: "1.55", maxWidth: "640px" }}>Yes. Billo is free to use in ASI:One and WhatsApp.</p>
          </details>
          <details style={{ background: "oklch(0.92 0.06 165)", borderRadius: "28px", padding: "0 28px" }}>
            <summary style={{ listStyle: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", minHeight: "76px", fontSize: "clamp(19px,2vw,24px)" }}>
              <span>Is this for emergencies?</span>
              <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: "22px" }}>+</span>
            </summary>
            <p style={{ margin: "0", padding: "0 0 26px", fontSize: "17px", lineHeight: "1.55", maxWidth: "640px" }}>No. If it might be an emergency, call 911 first. Billo checks for warning signs and will tell you to get help.</p>
          </details>
          <details style={{ background: "oklch(0.90 0.06 50)", borderRadius: "28px", padding: "0 28px" }}>
            <summary style={{ listStyle: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", minHeight: "76px", fontSize: "clamp(19px,2vw,24px)" }}>
              <span>Where do the prices come from?</span>
              <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: "22px" }}>+</span>
            </summary>
            <p style={{ margin: "0", padding: "0 0 26px", fontSize: "17px", lineHeight: "1.55", maxWidth: "640px" }}>From public price lists that clinics and hospitals must share. They are expected prices, not a final quote.</p>
          </details>
          <details style={{ background: "oklch(0.91 0.06 300)", borderRadius: "28px", padding: "0 28px" }}>
            <summary style={{ listStyle: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", minHeight: "76px", fontSize: "clamp(19px,2vw,24px)" }}>
              <span>Does Billo take my money?</span>
              <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: "22px" }}>+</span>
            </summary>
            <p style={{ margin: "0", padding: "0 0 26px", fontSize: "17px", lineHeight: "1.55", maxWidth: "640px" }}>No. Billo never asks for your card. You say yes before any payment step.</p>
          </details>
          <details style={{ background: "oklch(0.91 0.05 235)", borderRadius: "28px", padding: "0 28px" }}>
            <summary style={{ listStyle: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", minHeight: "76px", fontSize: "clamp(19px,2vw,24px)" }}>
              <span>How do I move from ASI:One to WhatsApp?</span>
              <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: "22px" }}>+</span>
            </summary>
            <p style={{ margin: "0", padding: "0 0 26px", fontSize: "17px", lineHeight: "1.55", maxWidth: "640px" }}>Scan your Billo code or tap the link. Your booking, prices and bills move with you.</p>
          </details>
          <details style={{ background: "oklch(0.94 0.08 95)", borderRadius: "28px", padding: "0 28px" }}>
            <summary style={{ listStyle: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", minHeight: "76px", fontSize: "clamp(19px,2vw,24px)" }}>
              <span>Who can see my bills?</span>
              <span style={{ width: "36px", height: "36px", borderRadius: "50%", background: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: "22px" }}>+</span>
            </summary>
            <p style={{ margin: "0", padding: "0 0 26px", fontSize: "17px", lineHeight: "1.55", maxWidth: "640px" }}>Only you. Bills stay in your private chat and your private visit page.</p>
          </details>
        </div>
      </section>
      <section style={{ padding: "0 16px 16px" }}>
        <div style={{ maxWidth: "1400px", margin: "0 auto", background: "oklch(0.90 0.06 50)", borderRadius: "40px", padding: "110px 24px", textAlign: "center", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", width: "260px", height: "260px", borderRadius: "50%", background: "oklch(0.94 0.08 95)", left: "-60px", bottom: "-80px" }} />
          <div style={{ position: "absolute", width: "200px", height: "200px", borderRadius: "50%", background: "oklch(0.91 0.06 300)", right: "-40px", top: "-50px" }} />
          <h2 style={{ position: "relative", fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(52px,8vw,108px)", lineHeight: ".9", margin: "0 auto", maxWidth: "900px", letterSpacing: "-.02em" }}>
            Make every care dollar{" "}
            <em>count.</em>
          </h2>
          <div style={{ position: "relative", display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap", marginTop: "40px" }}>
            <button onClick={() => openChooser("asi")} style={{ display: "inline-flex", alignItems: "center", minHeight: "54px", padding: "0 28px", border: "0", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", fontFamily: "var(--font-body)", cursor: "pointer", fontSize: "16px" }}>Open in ASI:One</button>
            {" "}
            <button onClick={() => openChooser("whatsapp")} style={{ display: "inline-flex", alignItems: "center", minHeight: "54px", padding: "0 28px", border: "0", borderRadius: "99px", background: "var(--color-neutral-100)", color: "var(--color-text)", fontFamily: "var(--font-body)", cursor: "pointer", fontSize: "16px" }}>Text on WhatsApp</button>
          </div>
        </div>
        <footer style={{ maxWidth: "1400px", margin: "0 auto", padding: "22px 24px", display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap", fontSize: "12.5px", color: "var(--color-neutral-700)" }}>
          <span>Built at LA Hacks 2026 · Fetch.ai · Photon · Tiger Data · Sentry · Visa (simulated)</span>
        </footer>
      </section>
    </div>
  );
}
