import CareSearch from "@/components/CareSearch";
import CaseRecord from "@/components/CaseRecord";
import ChatPreview from "@/components/ChatPreview";
import Journey from "@/components/Journey";
import Logo from "@/components/Logo";
import StartButtons from "@/components/StartButtons";

const guardrails = [
  ["You call it", "Billo joins a group chat only after someone tags @Billo."],
  ["You approve it", "No booking, letter, settlement, or reminder is sent silently."],
  ["Rules decide", "AI reads and writes. Fixed rules make safety and billing decisions."],
  ["Private by design", "Health text and raw identity data stay out of Sentry traces."],
];

export default function Home() {
  return (
    <main id="top">
      <div className="emergency-bar">If this may be an emergency call 911. Billo does not diagnose.</div>
      <header className="site-header">
        <Logo />
        <nav aria-label="Main navigation">
          <a href="#how">How it works</a>
          <a href="#care">Find care</a>
          <a href="#after">After care</a>
          <a href="#safety">Safety</a>
        </nav>
        <a className="header-link" href="#start">Start with @Billo <span>↗</span></a>
      </header>

      <section className="hero section-shell">
        <div className="hero-copy">
          <p className="eyebrow">Care cost clarity from search to next step</p>
          <h1>Make every care <em>dollar</em> count.</h1>
          <p className="hero-lead">Billo helps people compare care before a visit, keep a simple record during it, and organize bills and reimbursement paths afterward.</p>
          <StartButtons />
          <div className="hero-proof"><span>One continuous case</span><span>No surprise actions</span><span>Works in group chat</span></div>
        </div>
        <ChatPreview />
      </section>

      <section className="marquee" aria-label="Billo capabilities">
        <div>COMPARE CARE <span>◆</span> TRACK THE VISIT <span>◆</span> READ THE BILL <span>◆</span> ORGANIZE BENEFITS <span>◆</span> YOU APPROVE</div>
      </section>

      <section className="content-section" id="how">
        <div className="section-heading split-heading">
          <div><p className="eyebrow">One thread from start to finish</p><h2>Care is complicated.<br />The next step should not be.</h2></div>
          <p>Billo connects the decisions people make before care with the paperwork they face after it. Start at any point and keep the context together.</p>
        </div>
        <Journey />
      </section>

      <section className="content-section finder-section" id="care">
        <div className="section-heading center-heading">
          <p className="eyebrow">Connected to the Billo Core API</p>
          <h2>See the tradeoffs before the waiting room.</h2>
          <p>Search uses the same price and provider service as the Fetch.ai care-finder agent.</p>
        </div>
        <CareSearch />
      </section>

      <section className="content-section record-section" id="after">
        <div className="record-copy">
          <p className="eyebrow">After care</p>
          <h2>A bill becomes a clear case record.</h2>
          <p>OCR reads the document. Deterministic checks compare the provider, estimate, visit log, and local price data. Billo then shows what is known, what needs review, and what you can do next.</p>
          <ul>
            <li><span>01</span> Confirm whether it is a paid receipt or an unpaid bill.</li>
            <li><span>02</span> Organize eligible reimbursement documents.</li>
            <li><span>03</span> Simulate guarded payment only after explicit approval.</li>
          </ul>
        </div>
        <CaseRecord />
      </section>

      <section className="content-section safety-section" id="safety">
        <div className="section-heading split-heading">
          <div><p className="eyebrow">Built-in guardrails</p><h2>Helpful without taking control.</h2></div>
          <p>Sentry watches the system, not the patient. Operational traces use keyed case hashes and scrub sensitive inputs before they leave a service.</p>
        </div>
        <div className="guard-grid">
          {guardrails.map(([title, text], index) => (
            <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{text}</p></article>
          ))}
        </div>
      </section>

      <section className="closing-section">
        <div><p className="eyebrow">Start where you are</p><h2>Before the visit.<br />After the bill.<br /><em>One @Billo.</em></h2></div>
        <div><p>Bring Billo into a group chat by tagging @Billo. It stays quiet until called and keeps every next step visible.</p><StartButtons dark /></div>
      </section>

      <footer>
        <Logo />
        <p>Make every care dollar count.</p>
        <div><a href="#how">How it works</a><a href="#safety">Privacy</a><a href="mailto:hello@heybillo.tech">Contact</a></div>
        <small>© 2026 Billo · Not medical, legal, or financial advice.</small>
      </footer>
    </main>
  );
}
