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

test("each original feature card selects its inline simulation", () => {
  for (const step of ["safety", "prices", "estimate", "visit", "scan", "match", "payment", "benefits"]) {
    assert.match(landing, new RegExp(`featureCard\\("${step}"\\)`));
  }
  assert.match(landing, /FeatureSimulation step=\{featureStep\}/);
  assert.match(landing, /aria-pressed/);
});

test("feature simulations support mouse and keyboard interaction", () => {
  assert.match(landing, /role: "button"/);
  assert.match(landing, /event\.key !== "Enter" && event\.key !== " "/);
  assert.match(landing, /setFeatureStep/);
});

test("the original card grid remains below the embedded simulation", () => {
  assert.doesNotMatch(landing, /BilloSimulation/);
  assert.match(landing, /className=\{hv\.featureGrid\}/);
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
