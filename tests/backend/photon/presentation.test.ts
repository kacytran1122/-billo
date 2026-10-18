import assert from "node:assert/strict";
import test from "node:test";
import { BILLO_SCREENS, BILLO_WEBSITE, presentMessage } from "../../../backend/photon/src/presentation.ts";

test("WhatsApp gives a short headline native bold without changing amounts or actions", () => {
  assert.equal(presentMessage("🧾 Receipt organized\n\nTotal · $360.00\n@Billo check my HSA", "whatsapp_business"), `*🧾 Receipt organized*\n\n*Total · $360.00*\n@Billo check my HSA\n\nReview the organized charges (demo)\n${BILLO_SCREENS.match}`);
});
test("existing formatting, long text, and non-WhatsApp channels are preserved", () => {
  for (const text of ["", "a".repeat(91)]) assert.equal(presentMessage(text, "whatsapp_business"), text);
  assert.equal(presentMessage("*Already bold*\nDetails", "whatsapp_business"), "*Already bold*\n\nDetails");
  assert.equal(presentMessage("Hello\nDetails", "imessage"), "Hello\nDetails");
});

test("public website link is clean, is not duplicated, and formatting is idempotent", () => {
  const result = presentMessage("👋 Meet Billo\nTry @Billo help", "whatsapp_business");
  assert.equal(presentMessage(result, "whatsapp_business"), result);
  assert.equal(result.split(BILLO_WEBSITE).length - 1, 1);
  assert.doesNotMatch(result, /\]\(|case_id|token=|handle=/);
  const existing = presentMessage(`👋 Meet Billo\n${BILLO_WEBSITE}/#features`, "whatsapp_business");
  assert.equal(existing.split(BILLO_WEBSITE).length - 1, 1);
});

test("summary types receive their own public demo screen", () => {
  assert.match(presentMessage("📍 Your care shortlist\nThree options", "whatsapp_business"), /\/tools\/prices$/);
  assert.match(presentMessage("Care plan saved\nSample clinic", "whatsapp_business"), /\/tools\/estimate$/);
  assert.match(presentMessage("💸 Explore benefit paths\nTwo possibilities", "whatsapp_business"), /\/tools\/benefits$/);
});

test("progress, opt-out and emergency replies have no promotional footer", () => {
  for (const text of ["📸 Reading your bill", "🔎 Checking clinic QR", "✅ Stopped. Reminders canceled.", "Call 911 now."]) {
    assert.doesNotMatch(presentMessage(text, "whatsapp_business"), /getbillo\.us/);
  }
});
