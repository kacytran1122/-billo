import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);
const journey = readFileSync(
  new URL("../../../frontend/src/features/journey/JourneyScreen.tsx", import.meta.url),
  "utf8",
);
const journeyStyles = readFileSync(
  new URL("../../../frontend/src/features/journey/JourneyScreen.module.css", import.meta.url),
  "utf8",
);

test("journey cards open dedicated full-screen stages", () => {
  for (const stage of ["booked", "during", "verified", "payment"]) {
    assert.match(landing, new RegExp(`href="/journey/${stage}"`));
  }
});

test("full-screen journey preserves ordered before-to-after navigation", () => {
  assert.match(journey, /JOURNEY_STAGES = \["booked", "during", "verified", "payment"\]/);
  assert.match(journeyStyles, /min-height: 100svh/);
  assert.doesNotMatch(journey, /phoneFrame/);
});
