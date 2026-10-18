import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);
const modal = readFileSync(
  new URL("../../../frontend/src/features/simulation/FeatureSimulationModal.tsx", import.meta.url),
  "utf8",
);
const modalStyles = readFileSync(
  new URL("../../../frontend/src/features/simulation/FeatureSimulationModal.module.css", import.meta.url),
  "utf8",
);

test("each original feature card opens its own full-screen simulation", () => {
  for (const step of ["safety", "prices", "estimate", "visit", "scan", "match", "payment", "benefits"]) {
    assert.match(landing, new RegExp(`featureCard\\("${step}"\\)`));
  }
  assert.match(landing, /FeatureSimulationModal/);
  assert.match(landing, /aria-haspopup/);
});

test("feature simulations support mouse and keyboard interaction", () => {
  assert.match(landing, /role: "button"/);
  assert.match(landing, /event\.key !== "Enter" && event\.key !== " "/);
  assert.match(landing, /setFeatureStep/);
});

test("the original card grid remains while simulations render in a dialog", () => {
  assert.doesNotMatch(landing, /BilloSimulation/);
  assert.match(landing, /className=\{hv\.featureGrid\}/);
});

test("simulation matches the full case-workspace reference", () => {
  assert.match(modal, /role="dialog"/);
  assert.match(modal, /Case 8F2A · private demo/);
  assert.match(modal, /COMPARE CARE/);
  assert.match(modal, /Westwood Urgent Care/);
  assert.match(modalStyles, /position: fixed/);
});

test("simulation can complete reset and close", () => {
  assert.match(modal, /setComplete\(true\)/);
  assert.match(modal, /setComplete\(false\)/);
  assert.match(modal, /event\.key === "Escape"/);
  assert.match(modal, /onClick=\{onClose\}/);
});
