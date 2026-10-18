import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  caseDataLabel,
  documentNeedsReview,
  documentReviewTitle,
  formatMoney,
  isDemoMode,
  safeWebUrl,
} from "../../../frontend/src/lib/case-view.ts";

const source = (path: string) => readFileSync(new URL(`../../../frontend/src/${path}`, import.meta.url), "utf8");
const visitRoute = source("app/visit/[token]/page.tsx");
const continueRoute = source("app/continue/[token]/page.tsx");
const walletRoute = source("app/wallet/[token]/page.tsx");
const visitScreen = source("features/case/CaseScreen.tsx");
const handoffScreen = source("features/case/HandoffScreen.tsx");
const walletScreen = source("features/case/WalletScreen.tsx");
const config = source("../next.config.ts");

test("private conversation screens are dynamic, token-scoped, and fail closed", () => {
  for (const route of [visitRoute, continueRoute, walletRoute]) {
    assert.match(route, /dynamic = "force-dynamic"/);
    assert.match(route, /notFound\(\)/);
    assert.match(route, /robots: \{ index: false/);
    assert.match(route, /referrer: "no-referrer"/);
  }
  assert.match(visitRoute, /\/public\/cases\//);
  assert.match(walletRoute, /\/public\/wallet\//);
  assert.match(continueRoute, /\/api\/link\//);
});

test("visit, handoff, and wallet values come from their server payloads", () => {
  assert.match(visitScreen, /view\.provider\?\.name/);
  assert.match(visitScreen, /estimate\.amount/);
  assert.match(visitScreen, /No pre-visit estimate/);
  assert.match(visitScreen, /view\.visit\?\.items/);
  assert.match(visitScreen, /view\.document\.total/);
  assert.match(handoffScreen, /view\.deep_link/);
  assert.match(walletScreen, /view\.merchant_name/);
  assert.match(walletScreen, /view\.amount/);
  for (const hardcoded of ["BILLO-4821", "Westwood Urgent Care", "$240", "$310", "$360"]) {
    assert.doesNotMatch(visitScreen + handoffScreen + walletScreen, new RegExp(hardcoded.replace("$", "\\$")));
  }
});

test("private routes send defense-in-depth browser headers", () => {
  for (const value of ["private, no-store", "no-referrer", "DENY", "noindex, nofollow", "frame-ancestors 'none'", "payment=()"])
    assert.ok(config.includes(value), value);
  for (const route of ["/visit/:path*", "/continue/:path*", "/wallet/:path*"]) assert.ok(config.includes(route));
});

test("money and provenance formatting are explicit", () => {
  assert.equal(formatMoney(187.25), "$187.25");
  assert.equal(isDemoMode("demo"), true);
  assert.equal(isDemoMode("synthetic"), true);
  assert.equal(isDemoMode("live"), false);
  assert.equal(isDemoMode("patient_provided"), false);
  assert.equal(caseDataLabel("mixed"), "Mixed demo + case data");
  assert.equal(caseDataLabel("demo"), "Demo data");
  assert.equal(caseDataLabel("patient_provided"), "Case data");
  assert.equal(safeWebUrl("javascript:alert(1)"), "");
  assert.equal(safeWebUrl("https://evil.test/path", ["wa.me"]), "");
  assert.match(safeWebUrl("https://wa.me/15551234567?text=hello", ["wa.me"]), /^https:\/\/wa\.me\//);
});

test("document review state and neutral titles follow the public case contract", () => {
  assert.equal(documentReviewTitle("receipt"), "Your receipt review");
  assert.equal(documentReviewTitle("bill"), "Your bill review");
  assert.equal(documentReviewTitle("unknown"), "Your bill or receipt review");
  assert.equal(documentNeedsReview({ total: 10, review_status: "organized" }), false);
  assert.equal(documentNeedsReview({ total: 10, review_status: "review_needed" }), true);
  assert.equal(documentNeedsReview({ total: 10, unreviewed_lines: [2] }), true);
  assert.match(visitScreen, /line\.needs_review/);
  assert.match(visitScreen, /line\.review_reasons/);
  assert.match(visitScreen, /fallback_reason/);
});
