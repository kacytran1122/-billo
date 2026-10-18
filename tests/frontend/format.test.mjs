import assert from "node:assert/strict";
import test from "node:test";

import { buildSmsUrl, formatMoney, normalizePlaces } from "../../frontend/lib/format.js";

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

test("builds the iMessage handoff without exposing a secret", () => {
  const url = buildSmsUrl("+13105550199", "@Billo start");
  assert.match(url, /^sms:\+13105550199/);
  assert.match(url, /%40Billo%20start/);
  assert.equal(buildSmsUrl(""), "#start");
});
