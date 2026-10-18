import assert from "node:assert/strict";
import test from "node:test";
import { configuredChannels, destination, destinationKey } from "../../../backend/photon/src/channels.ts";

test("existing deployments default to iMessage only", () => {
  assert.deepEqual(configuredChannels(), ["imessage"]);
});
test("WhatsApp can be enabled alone or alongside iMessage", () => {
  assert.deepEqual(configuredChannels("whatsapp_business"), ["whatsapp_business"]);
  assert.deepEqual(configuredChannels("imessage, whatsapp_business,imessage"), ["imessage", "whatsapp_business"]);
});
test("invalid or empty channel settings fail explicitly", () => {
  for (const value of ["", "telegram", "imessage,typo"]) assert.throws(() => configuredChannels(value));
});
test("legacy iMessage destinations remain unchanged", () => {
  assert.equal(destinationKey("imessage", "chat-123"), "chat-123");
  assert.deepEqual(destination("chat-123"), { channel: "imessage", id: "chat-123" });
});
test("WhatsApp destinations round trip without colliding with iMessage", () => {
  const key = destinationKey("whatsapp_business", "chat:123");
  assert.notEqual(key, destinationKey("imessage", "chat:123"));
  assert.deepEqual(destination(key), { channel: "whatsapp_business", id: "chat:123" });
});
