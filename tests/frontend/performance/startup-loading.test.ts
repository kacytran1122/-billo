import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const component = readFileSync(
  new URL("../../../frontend/src/components/loading/LandingIntro.tsx", import.meta.url),
  "utf8",
);
const styles = readFileSync(
  new URL("../../../frontend/src/components/loading/LandingIntro.module.css", import.meta.url),
  "utf8",
);
const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);

test("landing page starts behind a dedicated app-style loader", () => {
  assert.match(landing, /<LandingIntro \/>/);
  assert.match(component, /role="status"/);
  assert.match(component, /aria-label="Loading Billo"/);
  assert.match(component, /setState\("hidden"\)/);
});

test("launch loader has progress, exit, and reduced-motion states", () => {
  assert.match(styles, /\.intro\[data-state="leaving"\]/);
  assert.match(styles, /@keyframes load/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});

test("lower landing sections are no longer delayed", () => {
  assert.doesNotMatch(landing, /LazySection|deferredSection/);
});
