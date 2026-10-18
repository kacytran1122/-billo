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
const homeSource = readFileSync(
  new URL("../../../frontend/src/app/page.tsx", import.meta.url),
  "utf8",
);
const connectStyles = readFileSync(
  new URL("../../../frontend/src/features/connect/ChannelConnect.module.css", import.meta.url),
  "utf8",
);

test("the first hero shows only the iMessage phone", () => {
  assert.match(homeSource, /heroPhones="iMessage only"/);
  assert.match(landingSource, /data-single/);
  assert.match(landingStyles, /heroPhones\[data-single="true"\]/);
  assert.match(landingStyles, /block-size: 548px/);
  assert.match(landingStyles, /transform: translateX\(-50%\) scale\(\.86\)/);
});

test("responsive navigation is CSS-driven without hydration-sensitive width state", () => {
  assert.doesNotMatch(landingSource, /window\.innerWidth/);
  assert.match(landingSource, /desktopNavigation/);
  assert.match(landingSource, /mobileMenuButton/);
  assert.match(landingStyles, /@media \(max-width: 900px\)/);
});

test("phone, tablet, laptop, and wide layouts have explicit balance rules", () => {
  assert.match(landingStyles, /@media \(max-width: 390px\)/);
  assert.match(landingStyles, /@media \(min-width: 700px\) and \(max-width: 1099px\)/);
  assert.match(landingStyles, /@media \(min-width: 901px\)/);
  assert.match(landingStyles, /@media \(max-width: 1180px\)/);
  assert.match(landingStyles, /grid-template-columns: 1fr/);
});

test("the ASI One to iMessage handoff arrows follow the layout direction", () => {
  assert.match(landingStyles, /@media \(min-width: 901px\)[\s\S]*\.caseFlow > svg \{ align-self: center; rotate: 0deg; \}/);
  assert.match(landingStyles, /@media \(max-width: 900px\)[\s\S]*\.caseFlow > svg \{ align-self: center; rotate: 90deg; \}/);
  assert.match(landingStyles, /grid-template-columns: minmax\(220px, 300px\) 36px auto 36px minmax\(220px, 300px\)/);
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
  assert.match(landingStyles, /@media \(max-width: 699px\)[\s\S]*grid-template-columns: minmax\(0, 1fr\) clamp\(124px, 36vw, 180px\)/);
  assert.match(landingStyles, /@media \(max-width: 699px\)[\s\S]*\.heroPhones[\s\S]*grid-column: 2/);
  assert.match(landingStyles, /@media \(max-width: 390px\)[\s\S]*grid-template-columns: minmax\(0, 1fr\) 112px/);
  assert.match(landingStyles, /@media \(max-width: 390px\)[\s\S]*block-size: 266px/);
});

test("navigation section state is synchronized efficiently while scrolling", () => {
  assert.match(landingSource, /requestAnimationFrame\(updateActiveSection\)/);
  assert.match(landingSource, /getBoundingClientRect\(\)\.top <= marker/);
  assert.match(landingSource, /window\.addEventListener\("scroll", onScroll/);
  assert.match(landingSource, /progressRef\.current\.style\.transform/);
  assert.match(landingStyles, /\.scrollProgress > span/);
  assert.match(landingSource, /mobileSectionLabel/);
});

test("motion remains optional for users who request reduced motion", () => {
  assert.match(landingSource, /prefers-reduced-motion: reduce/);
  assert.match(landingStyles, /@media \(prefers-reduced-motion: reduce\)/);
});

test("secure channel preview stays side by side without overlapping on small screens", () => {
  assert.match(connectStyles, /\.body > \* \{ min-width: 0; \}/);
  assert.match(connectStyles, /@media \(max-width: 470px\)[\s\S]*overflow-x: hidden/);
  assert.match(connectStyles, /grid-template-columns: minmax\(96px, \.7fr\) minmax\(0, 1fr\)/);
  assert.match(connectStyles, /\.phone \{[\s\S]*width: 100%;[\s\S]*overflow: hidden/);
  assert.match(connectStyles, /@media \(max-width: 340px\)[\s\S]*grid-template-columns: 92px minmax\(0, 1fr\)/);
});
