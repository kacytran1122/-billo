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
test("SMS configuration fails before the legacy SDK can choose a provider", () => {
  const legacy = source.slice(source.indexOf("async function legacyTransport"), source.indexOf("async function main"));
  assert.match(legacy, /if \(channels\.includes\("sms"\)\) throw new Error\("Photon SMS requires PHOTON_API_VERSION=beta"\)/);
  assert.ok(legacy.indexOf("channels.includes") < legacy.indexOf('import("spectrum-ts")'));
});
test("Beta receives the explicit channel selection and outbound caches cannot cross channels", () => {
  assert.match(source, /new BetaTransport\([\s\S]*?env\("PHOTON_STATE_FILE"[^\n]*\n\s*channels,/);
  assert.match(source, /if \(!channels\.includes\(target\.channel\)\)/);
  assert.match(source, /cached\?\.__platform === target\.channel \? cached/);
  assert.match(source, /beta\.getSpace\(target\.id, target\.channel\)/);
  assert.match(source, /if \(!space \|\| space\.__platform !== target\.channel\)/);
});
test("attachment failures preserve the caption and explicit error for emergency-first coordinator routing", () => {
  assert.match(source, /const attachmentError = ev\.attachments\.length > 1 \? "multiple"/);
  assert.match(source, /const attachmentUrl = ev\.attachments\.length === 1 \? await upload\(ev\.attachments\[0\]\) : ""/);
  assert.match(source, /attachment_error: attachmentError/);
  assert.match(source, /attachment_url: attachmentUrl/);
  assert.ok(source.indexOf("if (!shouldRespond(rawText, isGroup)) return") < source.indexOf("const attachmentUrl ="));
  assert.ok(source.indexOf('"STOP", "UNSUBSCRIBE"') < source.indexOf("const attachmentUrl ="));
});
