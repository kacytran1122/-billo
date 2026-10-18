export default function CaseRecord() {
  return (
    <div className="record-window">
      <div className="record-toolbar"><span /><span /><span /><strong>Case 8F2A · private record</strong></div>
      <div className="record-body">
        <aside>
          <span className="record-active">Overview</span>
          <span>Visit log</span>
          <span>Documents</span>
          <span>Benefits</span>
        </aside>
        <main>
          <div className="record-title"><div><small>WESTWOOD URGENT CARE</small><h3>Knee injury visit</h3></div><span className="status-chip">In review</span></div>
          <div className="record-total"><p>Current organized total</p><strong>$2,140</strong><span>Estimate was $240</span></div>
          <div className="record-line"><span className="check">✓</span><div><strong>Provider matched</strong><small>NPI and location confirmed</small></div><b>Done</b></div>
          <div className="record-line"><span className="check">✓</span><div><strong>Receipt organized</strong><small>3 coded lines · 1 needs a question</small></div><b>Done</b></div>
          <div className="record-line"><span className="wait">2</span><div><strong>Possible benefit paths</strong><small>HSA receipt · out-of-network claim</small></div><b>Review</b></div>
        </main>
      </div>
    </div>
  );
}
