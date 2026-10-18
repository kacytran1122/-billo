import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const simulation = readFileSync(
  new URL("../../../frontend/src/features/simulation/BilloSimulation.tsx", import.meta.url),
  "utf8",
);
const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);

test("All you need is Billo includes the interactive simulation", () => {
  assert.match(landing, /<BilloSimulation \/>/);
  assert.match(simulation, /Compare care/);
  assert.match(simulation, /Review a case/);
});

test("care comparison uses the local API with a synthetic fallback", () => {
  assert.match(simulation, /fetch\(`\/api\/care\/search/);
  assert.match(simulation, /setPlaces\(DEMO_PLACES\)/);
  assert.match(simulation, /aria-busy=\{loading\}/);
});

test("case simulation exposes the four matching workspace views", () => {
  for (const tab of ["overview", "visit", "documents", "benefits"]) assert.match(simulation, new RegExp(`"${tab}"`));
  assert.match(simulation, /providers, prices, case details, and payment states are synthetic/i);
});
