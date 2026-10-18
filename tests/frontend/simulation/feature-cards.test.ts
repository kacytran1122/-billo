import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);

test("each original feature card has its own simulation", () => {
  for (const step of ["safety", "prices", "estimate", "visit", "scan", "match", "payment", "benefits"]) {
    assert.match(landing, new RegExp(`featureCard\\("${step}"\\)`));
    assert.match(landing, new RegExp(`featureHint\\("${step}"\\)`));
  }
});

test("feature simulations support mouse and keyboard interaction", () => {
  assert.match(landing, /aria-pressed/);
  assert.match(landing, /event\.key !== "Enter" && event\.key !== " "/);
  assert.match(landing, /setFeatureStep/);
});

test("large replacement simulator is removed to preserve the original design", () => {
  assert.doesNotMatch(landing, /BilloSimulation/);
});
