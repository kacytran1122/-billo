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
  assert.match(landingStyles, /@media \(max-width: 900px\)/);
});

test("phone, tablet, laptop, and wide layouts have explicit balance rules", () => {
  assert.match(landingStyles, /@media \(max-width: 390px\)/);
  assert.match(landingStyles, /@media \(min-width: 700px\) and \(max-width: 1099px\)/);
  assert.match(landingStyles, /@media \(min-width: 901px\) and \(max-width: 1099px\)/);
  assert.match(landingStyles, /@media \(max-width: 1180px\)/);
  assert.match(landingStyles, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(landingStyles, /grid-template-columns: 1fr/);
});

test("desktop navigation and hero use centered and side-by-side placement", () => {
  assert.match(landingStyles, /\.desktopNavigation nav[\s\S]*left: 50%/);
  assert.match(landingStyles, /translate: -50% 0/);
  assert.match(landingStyles, /@media \(min-width: 1100px\)/);
  assert.match(landingStyles, /\.heroPhones[\s\S]*grid-column: 2/);
});

test("phone previews become smaller beside the headline on compact screens", () => {
  assert.match(landingSource, /className=\{hv\.phoneFrame\}/);
  assert.match(landingStyles, /\.phoneFrame[\s\S]*transform: scale\(\.86\)/);
  assert.match(landingStyles, /\.phoneAsi,[\s\S]*inline-size: 250px/);
  assert.match(landingStyles, /@media \(min-width: 700px\) and \(max-width: 1099px\)[\s\S]*transform: scale\(\.5\)/);
  assert.match(landingStyles, /grid-template-columns: minmax\(280px, 1fr\) 306px/);
});

test("navigation section state is synchronized efficiently while scrolling", () => {
  assert.match(landingSource, /requestAnimationFrame\(updateActiveSection\)/);
  assert.match(landingSource, /getBoundingClientRect\(\)\.top <= marker/);
  assert.match(landingSource, /window\.addEventListener\("scroll", onScroll/);
  assert.match(landingSource, /progressRef\.current\.style\.transform/);
  assert.match(landingStyles, /\.scrollProgress > span/);
  assert.match(landingSource, /mobileSectionLabel/);
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
