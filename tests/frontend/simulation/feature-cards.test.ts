import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);
const modal = readFileSync(
  new URL("../../../frontend/src/features/simulation/FeatureSimulation.tsx", import.meta.url),
  "utf8",
);
const modalStyles = readFileSync(
  new URL("../../../frontend/src/features/simulation/FeatureSimulation.module.css", import.meta.url),
  "utf8",
);

test("all eight workflows are available in the inline simulation", () => {
  assert.match(landing, /FeatureSimulation step=\{featureStep\}/);
  for (const step of ["safety", "prices", "estimate", "visit", "scan", "match", "payment", "benefits"]) {
    assert.match(modal, new RegExp(`\\[\"${step}\"`));
  }
});

test("the old static feature cards are removed", () => {
  assert.doesNotMatch(landing, /className=\{hv\.featureGrid\}/);
  assert.doesNotMatch(landing, /Safety first/);
  assert.doesNotMatch(landing, /Show simulation/);
});

test("simulation matches the full case-workspace reference", () => {
  assert.match(modal, /Interactive Billo workflow simulation/);
  assert.match(modal, /Case 8F2A · interactive demo/);
  assert.match(modal, /COMPARE CARE/);
  assert.match(modal, /Westwood Urgent Care/);
  assert.match(modalStyles, /\.embed/);
  assert.doesNotMatch(modalStyles, /position: fixed/);
});

test("simulation can switch steps complete and reset inline", () => {
  assert.match(modal, /setComplete\(true\)/);
  assert.match(modal, /setComplete\(false\)/);
  assert.match(modal, /onStepChange/);
  assert.match(modal, /Simulation steps/);
});

test("simulation uses live care search and keeps payment QR", () => {
  assert.match(modal, /fetch\(`\/api\/care\/search/);
  assert.match(modal, /normalizePlaces/);
  assert.match(modal, /QRCells cells=\{PAYMENT_QR\}/);
  assert.match(modal, /Choose a bill to scan/);
});
