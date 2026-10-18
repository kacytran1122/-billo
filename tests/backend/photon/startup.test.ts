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
test("persistent logs never include a sender or phone suffix", () => {
  assert.doesNotMatch(source, /slice\(-4\)/);
  assert.doesNotMatch(source, /from \$\{[^}]*sender/);
  assert.doesNotMatch(source, /from \$\{mask/);
  assert.match(source, /\[bridge\] inbound \$\{chatKind\} \(\$\{rawText\.length\} chars/);
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
test("attachment privacy and emergency gates run before document upload", () => {
  assert.match(source, /if \(isGroup && hasAttachments\)/);
  assert.match(source, /else if \(hasAttachments && hasEmergencyCaption\(text\)\)/);
  assert.match(source, /attachmentUrl = await actions\.upload\(ev\.attachments\[0\]\)/);
  assert.match(source, /attachment_error: attachmentError/);
  assert.match(source, /attachment_url: attachmentUrl/);
  assert.ok(source.indexOf("if (isGroup && hasAttachments)") < source.indexOf("await actions.upload"));
  assert.ok(source.indexOf("hasEmergencyCaption(text)") < source.indexOf("await actions.upload"));
  assert.ok(source.indexOf("if (!shouldRespond(rawText, isGroup)) return") < source.indexOf("await actions.upload"));
  assert.ok(source.indexOf('"STOP", "UNSUBSCRIBE"') < source.indexOf("await actions.upload"));
});

test("WhatsApp handoff claims only an exact direct-chat code and never forwards the code text", () => {
  assert.match(source, /\^BILLO-\[A-Z0-9\]\{4\}-\[A-Z0-9\]\{4\}\$\/i/);
  assert.match(source, /!isGroup && space\.__platform === "whatsapp_business" && HANDOFF_CODE\.test\(text\)/);
  assert.match(source, /core\("\/link\/claim", \{[\s\S]*?code: text\.toUpperCase\(\)[\s\S]*?channel: space\.__platform/);
  assert.match(source, /text: "", is_group: false, case_id: claim\.case_id, handoff_claimed: true/);
  assert.ok(source.indexOf("HANDOFF_CODE.test(text)") < source.indexOf("if (!shouldRespond(rawText, isGroup)) return"));
  assert.match(source, /Return to ASI:One and ask Billo for a new WhatsApp handoff/);
  assert.doesNotMatch(source.slice(source.indexOf("const reason ="), source.indexOf("await space.send", source.indexOf("const reason ="))), /visit page/);
  const claimBlock = source.slice(source.indexOf('core("/link/claim"'), source.indexOf("if (claim.case_id"));
  assert.match(claimBlock, /catch \{/);
  assert.match(claimBlock, /handoff could not be verified/);
  assert.match(claimBlock, /typing\(space, false\)/);
});
