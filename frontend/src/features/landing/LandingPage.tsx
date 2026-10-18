"use client";

/**
 * Billo landing page (migrated from "Billo 1.html").
 * Sticky pill navigation with scroll-spy, a "where do you want to chat?"
 * chooser dialog, two hero phone mockups and scroll-reveal animations.
 */
import { Fragment, useCallback, useEffect, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
import Link from "next/link";
import { BilloLogo } from "@/components/BilloLogo";
import { BilloWord } from "@/components/BilloWord";
import { LandingIntro } from "@/components/loading/LandingIntro";
import { QRCells } from "@/components/QRCells";
import { makeQR } from "@/lib/qr";
import { FeatureSimulationModal, type FeatureStep } from "@/features/simulation/FeatureSimulationModal";
import hv from "./LandingPage.module.css";

export type HeroPhones = "Both" | "ASI:One only" | "iMessage only";

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
  const [featureStep, setFeatureStep] = useState<FeatureStep | null>(null);
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
  const openChooser = () => {
    setChooser(true);
    setMenu(false);
  };
  const closeChooser = () => setChooser(false);
  const stop = (e: MouseEvent) => e.stopPropagation();
  const links = SECTIONS.map(([id, label]) => ({
    label,
    href: "#" + id,
    go: jump(id),
    active: active === id,
    inactive: active !== id,
  }));
  const activeLabel = SECTIONS.find(([id]) => id === active)?.[1] ?? "Home";
  const showAsi = heroPhones !== "iMessage only";
  const showIMessage = heroPhones !== "ASI:One only";
  const qr = QR;
  const featureCard = (step: FeatureStep) => ({
    role: "button" as const,
    tabIndex: 0,
    "aria-haspopup": "dialog" as const,
    onClick: () => setFeatureStep(step),
    onKeyDown: (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      setFeatureStep(step);
    },
  });
  const featureHint = () => <span className={hv.simulateHint}>Open simulation →</span>;

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
              <button className={hv.hover2} onClick={openChooser} style={{ display: "flex", alignItems: "center", gap: "8px", minHeight: "44px", padding: "0 20px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", border: "0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "15px" }}>
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
            <button onClick={openChooser} style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "54px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", border: "0", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "17px", marginTop: "4px" }}>Get started →</button>
          </nav>
        )}
        <div className={hv.scrollProgress} aria-hidden="true">
          <span ref={progressRef} />
        </div>
      </header>
      {chooserOpen && (
        <div onClick={closeChooser} style={{ position: "fixed", inset: "0", zIndex: "100", background: "color-mix(in oklch, var(--color-text) 45%, transparent)", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div role="dialog" aria-modal="true" aria-label="Where do you want to start?" onClick={stop} style={{ position: "relative", width: "100%", maxWidth: "560px", background: "var(--color-neutral-100)", borderRadius: "36px", padding: "36px 28px 28px", boxShadow: "var(--shadow-lg)", boxSizing: "border-box", textAlign: "center" }}>
            <button onClick={closeChooser} aria-label="Close" style={{ position: "absolute", top: "16px", right: "16px", width: "40px", height: "40px", borderRadius: "50%", border: "0", background: "var(--color-neutral-200)", cursor: "pointer", color: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
            <h2 style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "44px", lineHeight: ".95", margin: "0" }}>
              Where do you{" "}
              <em>want to chat?</em>
            </h2>
            <p style={{ margin: "12px 0 0", fontSize: "16px", color: "var(--color-neutral-800)" }}>You can switch later. Your case moves with you.</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: "12px", marginTop: "28px" }}>
              <Link className={hv.hover4} href="/prototype#asi" style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "14px", background: "oklch(0.94 0.08 95)", borderRadius: "26px", padding: "22px", color: "var(--color-text)", textDecoration: "none", textAlign: "left" }}>
                <span style={{ width: "44px", height: "44px", borderRadius: "12px", background: "var(--color-text)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "24px", color: "var(--color-accent-300)" }}>A</span>
                {" "}
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "28px", lineHeight: "1" }}>ASI:One</span>
                {" "}
                <span style={{ fontSize: "14px", lineHeight: "1.4" }}>Compare 3 nearby prices and book.</span>
                {" "}
                <span style={{ marginTop: "auto", fontSize: "15px" }}>Start →</span>
              </Link>
              {" "}
              <Link className={hv.hover4} href="/prototype#imsg" style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "14px", background: "oklch(0.91 0.05 235)", borderRadius: "26px", padding: "22px", color: "var(--color-text)", textDecoration: "none", textAlign: "left" }}>
                <span style={{ width: "44px", height: "44px", borderRadius: "12px", background: "oklch(0.6 0.17 255)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
                  </svg>
                </span>
                {" "}
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "28px", lineHeight: "1" }}>iMessage</span>
                {" "}
                <span style={{ fontSize: "14px", lineHeight: "1.4" }}>Text Billo and send a photo of your bill.</span>
                {" "}
                <span style={{ marginTop: "auto", fontSize: "15px" }}>Start →</span>
              </Link>
            </div>
          </div>
        </div>
      )}
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
            {" "}iMessage
          </div>
          <h1 className={hv.heroTitle} style={{ fontFamily: "var(--font-heading)", fontWeight: "400", fontSize: "clamp(56px,9vw,124px)", lineHeight: ".9", letterSpacing: "-.025em", margin: "26px auto 0", maxWidth: "980px", textWrap: "balance" }}>
            Make every care dollar{" "}
            <em style={{ color: "var(--color-accent-700)" }}>count.</em>
          </h1>
          <p className={hv.heroSubtitle} style={{ fontSize: "19px", lineHeight: "1.5", margin: "22px auto 0", maxWidth: "460px", color: "var(--color-neutral-800)" }}>Compare prices before. Check the bill after. All in one chat.</p>
          <div className={hv.heroActions} style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap", marginTop: "32px" }}>
            <Link href="/prototype#asi" style={{ display: "inline-flex", alignItems: "center", gap: "10px", minHeight: "54px", padding: "0 26px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", textDecoration: "none", fontSize: "16px" }}>
              <span style={{ width: "22px", height: "22px", borderRadius: "6px", border: "1.5px solid var(--color-accent-300)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: "14px", color: "var(--color-accent-300)" }}>A</span>
              Open in ASI:One
            </Link>
            {" "}
            <Link href="/prototype#imsg" style={{ display: "inline-flex", alignItems: "center", gap: "10px", minHeight: "54px", padding: "0 26px", borderRadius: "99px", background: "var(--color-neutral-100)", border: "1px solid var(--color-text)", color: "var(--color-text)", textDecoration: "none", fontSize: "16px" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="oklch(0.6 0.17 255)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
              </svg>
              Text on iMessage
            </Link>
          </div>
          <div className={hv.heroPhones} style={{ position: "relative", display: "flex", justifyContent: "center", alignItems: "flex-start", gap: "40px", flexWrap: "wrap", marginTop: "72px" }}>
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
                      <div style={{ alignSelf: "center", fontSize: "10px", color: "var(--color-neutral-600)" }}>iMessage · Today 4:12 PM</div>
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
                      <div style={{ flex: "1", border: "1px solid var(--color-neutral-300)", borderRadius: "18px", padding: "7px 12px", fontSize: "12px", color: "var(--color-neutral-600)" }}>iMessage</div>
                    </div>
                  </div>
                </div>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "22px", fontStyle: "italic" }}>After care · iMessage</span>
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
          <em>Continue in iMessage.</em>
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
              iMessage
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
        <div className={hv.featureGrid} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(min(100%,max(calc((100% - 60px) / 4),min(calc((100% - 20px) / 2),calc((270px - (100% - 60px) / 4) * 9999)))),1fr))", gridAutoRows: "1fr", gap: "20px", marginTop: "64px" }}>
          <div {...featureCard("safety")} className={hv.featureCard} style={{ background: "oklch(0.92 0.06 165)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>Safety first</div>
            <div style={{ marginTop: "auto", background: "var(--color-neutral-100)", borderRadius: "18px", padding: "16px", boxShadow: "var(--shadow-sm)", display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Chest pain</span>
                <span style={{ color: "var(--color-neutral-600)" }}>{featureStep === "safety" ? "Checked" : "No"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Trouble breathing</span>
                <span style={{ color: "var(--color-neutral-600)" }}>{featureStep === "safety" ? "Checked" : "No"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--color-divider)", paddingTop: "10px", fontWeight: "600" }}>
                <span>Emergency signs</span>
                <span>{featureStep === "safety" ? "Clear ✓" : "Clear"}</span>
              </div>
            </div>
            {featureHint()}
          </div>
          <div {...featureCard("prices")} className={hv.featureCard} style={{ background: "oklch(0.94 0.08 95)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>{featureStep === "prices" ? "Best price found" : "3 real prices"}</div>
            <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ background: featureStep === "prices" ? "var(--color-neutral-100)" : "transparent", borderRadius: "12px", padding: featureStep === "prices" ? "8px" : "0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "12.5px" }}>
                  <span>Campus Health</span>
                  <span style={{ fontVariantNumeric: "tabular-nums" }}>$120–$180</span>
                </div>
                <div style={{ position: "relative", height: "9px", borderRadius: "99px", background: "var(--color-neutral-100)", marginTop: "4px" }}>
                  <div style={{ position: "absolute", left: "6.67%", width: "3.33%", minWidth: "9px", top: "0", bottom: "0", borderRadius: "99px", background: "var(--color-text)" }} />
                </div>
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "12.5px" }}>
                  <span>Westwood Urgent</span>
                  <span style={{ fontVariantNumeric: "tabular-nums" }}>$180–$240</span>
                </div>
                <div style={{ position: "relative", height: "9px", borderRadius: "99px", background: "var(--color-neutral-100)", marginTop: "4px" }}>
                  <div style={{ position: "absolute", left: "10%", width: "3.33%", minWidth: "9px", top: "0", bottom: "0", borderRadius: "99px", background: "var(--color-text)" }} />
                </div>
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "12.5px" }}>
                  <span>Santa Monica ER</span>
                  <span style={{ fontVariantNumeric: "tabular-nums" }}>$1,200–$1,800</span>
                </div>
                <div style={{ position: "relative", height: "9px", borderRadius: "99px", background: "var(--color-neutral-100)", marginTop: "4px" }}>
                  <div style={{ position: "absolute", left: "66.67%", width: "33.33%", minWidth: "9px", top: "0", bottom: "0", borderRadius: "99px", background: "var(--color-text)" }} />
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--color-neutral-700)", fontVariantNumeric: "tabular-nums" }}>
                <span>$0</span>
                <span>low → typical, public price files</span>
                <span>$1,800</span>
              </div>
            </div>
            {featureHint()}
          </div>
          <div {...featureCard("estimate")} className={hv.featureCard} style={{ background: "oklch(0.90 0.06 50)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>{featureStep === "estimate" ? "Estimate saved ✓" : "Expected price"}</div>
            <div style={{ marginTop: "auto", background: "var(--color-neutral-100)", borderRadius: "18px", padding: "18px", boxShadow: "var(--shadow-sm)" }}>
              <div style={{ fontFamily: "var(--font-heading)", fontSize: "52px", lineHeight: "1", fontVariantNumeric: "tabular-nums" }}>$240.00</div>
              <div style={{ display: "flex", gap: "6px", marginTop: "12px", flexWrap: "wrap" }}>
                <span style={{ display: "inline-flex", gap: "5px", alignItems: "center", background: "oklch(0.91 0.05 235)", padding: "4px 10px", borderRadius: "99px", fontSize: "11px" }}>
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="18" height="18" x="3" y="4" rx="2" />
                    <path d="M16 2v4M8 2v4M3 10h18" />
                  </svg>
                  Tue 3:30 PM
                </span>
                {" "}
                <span style={{ background: "oklch(0.92 0.06 165)", padding: "4px 10px", borderRadius: "99px", fontSize: "11px" }}>Westwood</span>
              </div>
            </div>
            {featureHint()}
          </div>
          <div {...featureCard("visit")} className={hv.featureCard} style={{ background: "oklch(0.91 0.06 300)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>Log the visit</div>
            <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}>
              <div style={{ flexShrink: "0", alignSelf: "flex-end", background: "var(--color-text)", color: "var(--color-neutral-100)", padding: "8px 14px", borderRadius: "16px 16px 4px 16px" }}>
                <BilloWord />
                {" "}{featureStep === "visit" ? "they did an x-ray" : "tap to log a service"}
              </div>
              <div style={{ flexShrink: "0", alignSelf: "flex-start", background: "var(--color-neutral-100)", padding: "8px 14px", borderRadius: "16px 16px 16px 4px" }}>{featureStep === "visit" ? "Logged, about $120" : "Waiting for your update"}</div>
              <div style={{ flexShrink: "0", alignSelf: "flex-start", display: "flex", gap: "8px", alignItems: "baseline", background: "var(--color-neutral-100)", padding: "8px 14px", borderRadius: "16px" }}>
                <span>Expected</span>
                <span style={{ fontFamily: "var(--font-heading)", fontSize: "24px" }}>{featureStep === "visit" ? "≈ $360" : "$240"}</span>
              </div>
            </div>
            {featureHint()}
          </div>
          <div {...featureCard("scan")} className={hv.featureCard} style={{ background: "oklch(0.91 0.05 235)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>{featureStep === "scan" ? "Bill read ✓" : "Snap the bill"}</div>
            <div style={{ marginTop: "auto", display: "flex", justifyContent: "center" }}>
              <div style={{ position: "relative", width: "170px", background: "var(--color-neutral-100)", borderRadius: "12px", padding: "16px", boxShadow: "var(--shadow-md)", transform: "rotate(-4deg)" }}>
                <div style={{ fontSize: "10px", fontWeight: "600", letterSpacing: ".06em" }}>WESTWOOD URGENT CARE</div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginTop: "10px" }}>
                  <span>Office visit</span>
                  <span>240.00</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginTop: "4px" }}>
                  <span>X-ray, knee</span>
                  <span>120.00</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", fontWeight: "600", marginTop: "8px", borderTop: "1px dashed var(--color-neutral-400)", paddingTop: "6px" }}>
                  <span>Total</span>
                  <span>$360.00</span>
                </div>
                <div style={{ position: "absolute", left: "-8px", right: "-8px", top: "46%", height: "2px", background: "var(--color-accent)" }} />
                <div style={{ position: "absolute", inset: "-8px", border: "2px solid var(--color-text)", borderRadius: "16px", clipPath: "polygon(0 0,22% 0,22% 3px,3px 3px,3px 22%,0 22%,0 78%,3px 78%,3px calc(100% - 3px),22% calc(100% - 3px),22% 100%,78% 100%,78% calc(100% - 3px),calc(100% - 3px) calc(100% - 3px),calc(100% - 3px) 78%,100% 78%,100% 22%,calc(100% - 3px) 22%,calc(100% - 3px) 3px,78% 3px,78% 0,100% 0,100% 100%,0 100%)" }} />
              </div>
            </div>
            {featureHint()}
          </div>
          <div {...featureCard("match")} className={hv.featureCard} style={{ background: "var(--color-text)", color: "var(--color-neutral-100)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>
              Matched{" "}
              &amp;
              <em style={{ color: "var(--color-accent-300)" }}>explained</em>
            </div>
            <div style={{ marginTop: "auto", display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", fontFamily: "var(--font-heading)", fontVariantNumeric: "tabular-nums" }}>
              <span style={{ background: "oklch(0.90 0.06 50)", color: "var(--color-text)", borderRadius: "14px", padding: "8px 12px", fontSize: "28px" }}>$240</span>
              {" "}
              <span style={{ fontSize: "26px" }}>+</span>
              {" "}
              <span style={{ background: "oklch(0.91 0.06 300)", color: "var(--color-text)", borderRadius: "14px", padding: "8px 12px", fontSize: "28px" }}>{featureStep === "match" ? "$120" : "?"}</span>
              {" "}
              <span style={{ fontSize: "26px" }}>=</span>
              {" "}
              <span style={{ background: "oklch(0.92 0.06 165)", color: "var(--color-text)", borderRadius: "14px", padding: "8px 12px", fontSize: "28px" }}>{featureStep === "match" ? "$360" : "?"}</span>
            </div>
            <div style={{ fontSize: "13px", color: "var(--color-neutral-300)" }}>{featureStep === "match" ? "All lines verified ✓" : "Tap to match the bill to the visit"}</div>
            {featureHint()}
          </div>
          <div {...featureCard("payment")} className={hv.featureCard} style={{ background: "oklch(0.92 0.06 165)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>{featureStep === "payment" ? "Payment simulation ready" : "Pay the right clinic"}</div>
            <div style={{ marginTop: "auto", display: "flex", gap: "16px", alignItems: "center" }}>
              <div style={{ width: "96px", height: "96px", padding: "8px", background: "var(--color-neutral-100)", borderRadius: "14px", boxSizing: "border-box", display: "grid", gridTemplateColumns: "repeat(21,1fr)", gap: "0", flex: "none" }}>
                <QRCells cells={qr} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px" }}>
                <span>{featureStep === "payment" ? "✓ Right clinic" : "○ Check clinic"}</span>
                <span>{featureStep === "payment" ? "✓ Right amount" : "○ Check amount"}</span>
                <span>{featureStep === "payment" ? "✓ Right bill" : "○ Check bill"}</span>
                <span style={{ fontWeight: "600" }}>{featureStep === "payment" ? "Ready for your approval" : "You say yes first"}</span>
              </div>
            </div>
            {featureHint()}
          </div>
          <div {...featureCard("benefits")} className={hv.featureCard} style={{ background: "oklch(0.94 0.08 95)", borderRadius: "28px", padding: "24px", display: "flex", flexDirection: "column", gap: "22px", minHeight: "300px", minWidth: "0" }}>
            <div style={{ fontFamily: "var(--font-heading)", fontSize: "30px", lineHeight: "1" }}>{featureStep === "benefits" ? "HSA path found" : "Can you get money back?"}</div>
            <div style={{ marginTop: "auto", display: "flex", flexWrap: "wrap", gap: "8px" }}>
              <span style={{ background: featureStep === "benefits" ? "var(--color-text)" : "var(--color-neutral-100)", color: featureStep === "benefits" ? "var(--color-neutral-100)" : "var(--color-text)", padding: "7px 14px", borderRadius: "99px", fontSize: "13px" }}>HSA</span>
              {" "}
              <span style={{ background: "var(--color-neutral-100)", padding: "7px 14px", borderRadius: "99px", fontSize: "13px" }}>FSA</span>
              {" "}
              <span style={{ background: "var(--color-neutral-100)", padding: "7px 14px", borderRadius: "99px", fontSize: "13px" }}>Work plan</span>
              {" "}
              <span style={{ background: "var(--color-neutral-100)", padding: "7px 14px", borderRadius: "99px", fontSize: "13px" }}>School plan</span>
              {" "}
              <span style={{ background: "var(--color-neutral-100)", padding: "7px 14px", borderRadius: "99px", fontSize: "13px" }}>Travel insurance</span>
              {" "}
              <span style={{ border: "1px dashed var(--color-text)", padding: "6px 13px", borderRadius: "99px", fontSize: "13px", fontStyle: "italic" }}>{featureStep === "benefits" ? "Possible · review eligibility" : "Billo helps you check"}</span>
            </div>
            {featureHint()}
          </div>
        </div>
      </section>
      {featureStep && <FeatureSimulationModal step={featureStep} onClose={() => setFeatureStep(null)} />}
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
            <p style={{ margin: "0", padding: "0 0 26px", fontSize: "17px", lineHeight: "1.55", maxWidth: "640px" }}>Yes. Billo is free to use in ASI:One and iMessage.</p>
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
              <span>How do I move from ASI:One to iMessage?</span>
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
            <Link href="/prototype#asi" style={{ display: "inline-flex", alignItems: "center", minHeight: "54px", padding: "0 28px", borderRadius: "99px", background: "var(--color-text)", color: "var(--color-neutral-100)", textDecoration: "none", fontSize: "16px" }}>Open in ASI:One</Link>
            {" "}
            <Link href="/prototype#imsg" style={{ display: "inline-flex", alignItems: "center", minHeight: "54px", padding: "0 28px", borderRadius: "99px", background: "var(--color-neutral-100)", color: "var(--color-text)", textDecoration: "none", fontSize: "16px" }}>Text on iMessage</Link>
          </div>
        </div>
        <footer style={{ maxWidth: "1400px", margin: "0 auto", padding: "22px 24px", display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap", fontSize: "12.5px", color: "var(--color-neutral-700)" }}>
          <span>Built at LA Hacks 2026 · Fetch.ai · Photon · Tiger Data · Sentry · Visa (simulated)</span>
        </footer>
      </section>
    </div>
  );
}
