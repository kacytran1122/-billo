import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import { ASI_ONE_URL, whatsappDestination } from "../../../frontend/src/lib/channels.ts";

const connect = readFileSync(
  new URL("../../../frontend/src/features/connect/ChannelConnect.tsx", import.meta.url),
  "utf8",
);
const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);

test("ASI:One opens the public Billo agent", () => {
  assert.match(ASI_ONE_URL, /https:\/\/asi1\.ai\/ai\/agent1qdral3yq/);
  assert.match(connect, /Open \{current\.label\}/);
});

test("WhatsApp links prefill an explicit tag and never use SMS", () => {
  const url = new URL(whatsappDestination("https://wa.me/15551234567"));
  assert.equal(url.searchParams.get("text"), "@Billo help");
  assert.doesNotMatch(connect, /sms:|IMESSAGE_URL|imessage/);
});

test("connection QR codes encode real destinations", () => {
  assert.match(connect, /QRCode\.toDataURL\(destination/);
  assert.doesNotMatch(connect, /makeQR\("BILLO-4821"\)/);
});

test("WhatsApp never presents a fake working QR", () => {
  assert.equal(whatsappDestination(undefined), "");
  assert.match(connect, /WhatsApp is not connected yet/);
  assert.match(connect, /destination && qr/);
});

test("landing actions open the channel connection experience", () => {
  assert.match(landing, /<ChannelConnect open=\{chooserOpen\}/);
  assert.match(landing, /openChooser\("asi"\)/);
  assert.match(landing, /openChooser\("whatsapp"\)/);
  for (const feature of ["Emergency rules first", "Transparent care estimates", "Bill &amp; receipt OCR", "Benefit paths"]) {
    assert.match(landing, new RegExp(feature));
  }
});

test("untrusted and malformed WhatsApp destinations do not create QR links", () => {
  for (const value of ["javascript:alert(1)", "http://wa.me/15551234567", "https://evil.test/15551234567", "https://wa.me/abc", "https://wa.me.evil.test/15551234567", "https://user:pass@wa.me/15551234567"]) {
    assert.equal(whatsappDestination(value), "", value);
  }
});

test("public landing and prototype contain WhatsApp instead of iMessage calls to action", () => {
  for (const path of ["landing/LandingPage.tsx", "prototype/PrototypePage.tsx", "classic/ClassicLanding.tsx"]) {
    const source = readFileSync(new URL(`../../../frontend/src/features/${path}`, import.meta.url), "utf8");
    assert.doesNotMatch(source, /iMessage|sms:/);
    assert.match(source, /WhatsApp/);
  }
});

test("each channel action opens only its own connection window", () => {
  assert.match(connect, /const channel = initialChannel/);
  assert.doesNotMatch(connect, /CHANNELS\.map/);
  assert.doesNotMatch(connect, /setChannel/);
});

test("connection instructions use professional language", () => {
  assert.match(connect, /Secure channel access/);
  assert.match(connect, /Scan the QR code on another device or continue securely on this one\./);
  assert.doesNotMatch(connect, /Choose a live door/i);
});

test("the original walkthrough is preserved as future development", () => {
  const walkthrough = new URL("../../../Future Development/billo-walkthrough.html", import.meta.url);
  assert.equal(existsSync(walkthrough), true);
  assert.match(readFileSync(walkthrough, "utf8"), /Twenty-four hours was not enough/);
});
