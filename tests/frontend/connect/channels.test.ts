import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const connect = readFileSync(
  new URL("../../../frontend/src/features/connect/ChannelConnect.tsx", import.meta.url),
  "utf8",
);
const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);

test("ASI:One opens the public Billo agent", () => {
  assert.match(connect, /https:\/\/asi1\.ai\/ai\/agent1qdral3yq/);
  assert.match(connect, /Open \{current\.label\}/);
});

test("iMessage QR targets the live Photon line with an explicit tag", () => {
  assert.match(connect, /buildSmsUrl\("\+17739371364", "@Billo start"\)/);
  assert.match(connect, /Live via Photon/);
});

test("connection QR codes encode real destinations", () => {
  assert.match(connect, /QRCode\.toDataURL\(destination/);
  assert.doesNotMatch(connect, /makeQR\("BILLO-4821"\)/);
});

test("WhatsApp never presents a fake working QR", () => {
  assert.match(connect, /NEXT_PUBLIC_BILLO_WHATSAPP_URL/);
  assert.match(connect, /WhatsApp is not connected yet/);
  assert.match(connect, /destination && qr/);
});

test("landing actions open the channel connection experience", () => {
  assert.match(landing, /<ChannelConnect open=\{chooserOpen\}/);
  assert.match(landing, /openChooser\("asi"\)/);
  assert.match(landing, /openChooser\("imessage"\)/);
  for (const feature of ["Emergency rules first", "Real care prices", "Bill &amp; receipt OCR", "Benefit paths"]) {
    assert.match(landing, new RegExp(feature));
  }
});

test("the original walkthrough is preserved as future development", () => {
  const walkthrough = new URL("../../../Future Development/billo-walkthrough.html", import.meta.url);
  assert.equal(existsSync(walkthrough), true);
  assert.match(readFileSync(walkthrough, "utf8"), /Twenty-four hours was not enough/);
});
