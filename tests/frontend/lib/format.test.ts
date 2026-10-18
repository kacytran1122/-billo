import assert from "node:assert/strict";
import test from "node:test";

import { buildSmsUrl, formatMoney, normalizePlaces, sanitizeSmsAddress } from "../../../frontend/src/lib/format.ts";
import { normalizeCareSearch } from "../../../frontend/src/lib/search.ts";

test("formats care costs as whole US dollars", () => {
  assert.equal(formatMoney(240), "$240");
  assert.equal(formatMoney("1900"), "$1,900");
  assert.equal(formatMoney("unknown"), "—");
});

test("normalizes at most three safe place summaries", () => {
  const places = normalizePlaces({ places: Array.from({ length: 5 }, (_, index) => ({
    name: `Clinic ${index}`,
    price_low: 100 + index,
    price_typical: 200 + index,
  })) });
  assert.equal(places.length, 3);
  assert.equal(places[0].name, "Clinic 0");
  assert.equal(places[0].address, "Address unavailable");
});

test("rejects malformed place payloads and clamps negative prices", () => {
  assert.deepEqual(normalizePlaces(null), []);
  assert.deepEqual(normalizePlaces({ places: "not-an-array" }), []);
  const [place] = normalizePlaces({ places: [{ price_low: -10, price_typical: "not-a-number" }] });
  assert.equal(place.low, 0);
  assert.equal(place.typical, 0);
});

test("builds the iMessage handoff without exposing a secret", () => {
  const url = buildSmsUrl("+13105550199", "@Billo start");
  assert.match(url, /^sms:\+13105550199/);
  assert.match(url, /%40Billo%20start/);
  assert.equal(buildSmsUrl(""), "#start");
});

test("normalizes supported phone and email iMessage addresses", () => {
  assert.equal(sanitizeSmsAddress(" +1 (310) 555-0199 "), "+13105550199");
  assert.equal(sanitizeSmsAddress("billo@example.com"), "billo@example.com");
});

test("rejects unsafe SMS addresses", () => {
  assert.equal(sanitizeSmsAddress("+13105550199&body=override"), "");
  assert.equal(sanitizeSmsAddress("javascript:alert(1)"), "");
  assert.equal(buildSmsUrl("javascript:alert(1)"), "#start");
});

test("care search trims input and supplies defaults", () => {
  const empty = normalizeCareSearch(new URLSearchParams("q=%20%20&near="));
  assert.deepEqual(empty, { q: "routine visit", near: "UCLA" });
  const filled = normalizeCareSearch(new URLSearchParams("q=%20knee%20pain%20&near=%20Westwood%20"));
  assert.deepEqual(filled, { q: "knee pain", near: "Westwood" });
});

test("care search enforces backend-compatible input limits", () => {
  const result = normalizeCareSearch(new URLSearchParams({ q: "q".repeat(220), near: "n".repeat(100) }));
  assert.equal(result.q.length, 160);
  assert.equal(result.near.length, 80);
});
