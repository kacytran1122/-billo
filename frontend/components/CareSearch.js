"use client";

import { useState } from "react";
import { formatMoney, normalizePlaces } from "@/lib/format";

export default function CareSearch() {
  const [query, setQuery] = useState("knee pain after a fall");
  const [near, setNear] = useState("UCLA");
  const [places, setPlaces] = useState([]);
  const [status, setStatus] = useState("idle");

  async function search(event) {
    event.preventDefault();
    setStatus("loading");
    try {
      const response = await fetch(`/api/care/search?q=${encodeURIComponent(query)}&near=${encodeURIComponent(near)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error);
      setPlaces(normalizePlaces(payload));
      setStatus("ready");
    } catch {
      setPlaces([]);
      setStatus("error");
    }
  }

  return (
    <div className="finder-panel">
      <form onSubmit={search} className="finder-form">
        <label>
          What happened?
          <input value={query} onChange={(event) => setQuery(event.target.value)} maxLength={160} />
        </label>
        <label>
          Near
          <input value={near} onChange={(event) => setNear(event.target.value)} maxLength={80} />
        </label>
        <button className="button button-primary" disabled={status === "loading"}>
          {status === "loading" ? "Checking…" : "Compare care"}
        </button>
      </form>

      <div className="finder-results" aria-live="polite">
        {status === "idle" && <div className="finder-empty"><span>↳</span> Try the live care search.</div>}
        {status === "error" && <div className="finder-empty error">The Core API is offline. Start it with <code>make core</code>.</div>}
        {places.map((place, index) => (
          <article className="place-card" key={`${place.name}-${index}`}>
            <div className="place-rank">0{index + 1}</div>
            <div>
              <div className="place-heading"><h3>{place.name}</h3><span>{place.kind}</span></div>
              <p>{place.address} · {place.hours}</p>
              <small>{place.source}</small>
            </div>
            <div className="price"><span>typical</span><strong>{formatMoney(place.typical)}</strong><small>from {formatMoney(place.low)}</small></div>
          </article>
        ))}
      </div>
    </div>
  );
}
