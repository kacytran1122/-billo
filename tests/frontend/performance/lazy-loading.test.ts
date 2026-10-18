import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const component = readFileSync(
  new URL("../../../frontend/src/components/lazy/LazySection.tsx", import.meta.url),
  "utf8",
);
const styles = readFileSync(
  new URL("../../../frontend/src/components/lazy/LazySection.module.css", import.meta.url),
  "utf8",
);
const landing = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);

test("lower landing sections mount near the viewport", () => {
  assert.match(component, /new IntersectionObserver/);
  assert.match(component, /rootMargin: "500px 0px"/);
  assert.match(component, /loaded \? \(/);
  assert.ok((landing.match(/<LazySection/g) ?? []).length >= 3);
});

test("lazy placeholders use accessible social-style skeletons", () => {
  assert.match(component, /role="status"/);
  assert.match(component, /aria-label="Loading section"/);
  assert.match(styles, /@keyframes shimmer/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});
