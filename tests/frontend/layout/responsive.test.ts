import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const landingSource = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.tsx", import.meta.url),
  "utf8",
);
const landingStyles = readFileSync(
  new URL("../../../frontend/src/features/landing/LandingPage.module.css", import.meta.url),
  "utf8",
);

test("responsive navigation is CSS-driven without hydration-sensitive width state", () => {
  assert.doesNotMatch(landingSource, /window\.innerWidth/);
  assert.match(landingSource, /desktopNavigation/);
  assert.match(landingSource, /mobileMenuButton/);
  assert.match(landingStyles, /@media \(max-width: 720px\)/);
});

test("phone, tablet, laptop, and wide layouts have explicit balance rules", () => {
  assert.match(landingStyles, /@media \(max-width: 390px\)/);
  assert.match(landingStyles, /@media \(min-width: 721px\) and \(max-width: 900px\)/);
  assert.match(landingStyles, /@media \(max-width: 1180px\)/);
  assert.match(landingStyles, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(landingStyles, /grid-template-columns: 1fr/);
});

test("below-the-fold sections use browser-native lazy rendering", () => {
  const deferredUses = landingSource.match(/hv\.deferredSection/g) ?? [];
  assert.ok(deferredUses.length >= 3);
  assert.match(landingStyles, /content-visibility: auto/);
  assert.match(landingStyles, /contain-intrinsic-block-size: auto 760px/);
});

test("motion remains optional for users who request reduced motion", () => {
  assert.match(landingSource, /prefers-reduced-motion: reduce/);
  assert.match(landingStyles, /@media \(prefers-reduced-motion: reduce\)/);
});
