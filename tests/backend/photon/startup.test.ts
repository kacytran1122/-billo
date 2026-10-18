import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../../../backend/photon/src/main.ts", import.meta.url), "utf8");
test("Photon Beta startup never eagerly loads the legacy Spectrum SDK", () => {
  assert.match(source, /import type \{ Message, Space \} from "spectrum-ts"/);
  assert.doesNotMatch(source, /^import (?!type)[^\n]*from "spectrum-ts/m);
  assert.match(source, /const legacy = beta \? undefined : await legacyTransport\(channels\)/);
});
test("bridge readiness requires the live Photon event subscription", () => {
  assert.match(source, /state\?\.connected && state\?\.subscribed/);
  assert.match(source, /res\.statusCode = ready \? 200 : 503/);
  assert.match(source, /ok: ready/);
});
test("gateway and core requests have bounded timeouts", () => {
  assert.equal(source.match(/signal: AbortSignal\.timeout\(15_000\)/g)?.length, 2);
});
