"use client";

import { buildSmsUrl } from "@/lib/format";

export default function StartButtons({ dark = false }) {
  const asiUrl = process.env.NEXT_PUBLIC_ASI_ONE_URL || "https://asi1.ai";
  const line = process.env.NEXT_PUBLIC_PHOTON_LINE_ADDRESS || "";

  return (
    <div className={`start-buttons ${dark ? "on-dark" : ""}`} id="start">
      <a className="button button-primary" href={asiUrl} target="_blank" rel="noreferrer">
        Open ASI:One <span aria-hidden="true">↗</span>
      </a>
      <a className="button button-quiet" href={buildSmsUrl(line)}>
        Tag @Billo in iMessage
      </a>
    </div>
  );
}
