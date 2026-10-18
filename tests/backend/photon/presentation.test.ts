import assert from "node:assert/strict";
import test from "node:test";
import { BILLO_WEBSITE, presentMessage } from "../../../backend/photon/src/presentation.ts";

test("WhatsApp gives a short headline native bold without changing amounts or actions", () => {
  assert.equal(
    presentMessage("🧾 Receipt organized\n\nTotal · $360.00\n@Billo check my HSA", "whatsapp_business"),
    "*🧾 Receipt organized*\n\n*Total · $360.00*\n@Billo check my HSA",
  );
});
test("existing formatting, long text, and non-WhatsApp channels are preserved", () => {
  for (const text of ["", "a".repeat(91)]) assert.equal(presentMessage(text, "whatsapp_business"), text);
  assert.equal(presentMessage("*Already bold*\nDetails", "whatsapp_business"), "*Already bold*\n\nDetails");
  assert.equal(presentMessage("Hello\nDetails", "imessage"), "Hello\nDetails");
});

test("Coordinator-selected private link is preserved once and formatting is idempotent", () => {
  const visitUrl = `${BILLO_WEBSITE}/visit/opaque-token#after`;
  const result = presentMessage(`🧾 Receipt organized\nOpen your bill summary:\n${visitUrl}`, "whatsapp_business");
  assert.equal(presentMessage(result, "whatsapp_business"), result);
  assert.equal(result.split(visitUrl).length - 1, 1);
  assert.doesNotMatch(result, /\]\(|case_id|token=|handle=/);
  const existing = presentMessage(`👋 Meet Billo\n${BILLO_WEBSITE}/#features`, "whatsapp_business");
  assert.equal(existing.split(BILLO_WEBSITE).length - 1, 1);
});

test("presentation formats only and never chooses or invents a screen URL", () => {
  for (const text of ["📍 Your care shortlist\nThree options", "Care plan saved\nSample clinic", "💸 Explore benefit paths\nTwo possibilities"]) {
    assert.doesNotMatch(presentMessage(text, "whatsapp_business"), /getbillo\.us/);
  }
});

test("progress, opt-out and emergency replies have no promotional footer", () => {
  for (const text of ["📸 Reading your bill", "🔎 Checking clinic QR", "✅ Stopped. Reminders canceled.", "Call 911 now."]) {
    assert.doesNotMatch(presentMessage(text, "whatsapp_business"), /getbillo\.us/);
  }
});
