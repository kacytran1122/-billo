import assert from "node:assert/strict";
import test from "node:test";

import { hasBilloMention, shouldRespond, stripBilloMention } from "../../../backend/photon/src/routing.ts";

test("chat activation recognizes @Billo case-insensitively", () => {
  assert.equal(hasBilloMention("@Billo find urgent care near UCLA"), true);
  assert.equal(hasBilloMention("hey @BILLO can you help"), true);
  assert.equal(hasBilloMention("Billo can you help"), false);
});

test("mention is removed before private or group routing", () => {
  assert.equal(stripBilloMention("@Billo find care"), "find care");
  assert.equal(stripBilloMention("hello @BILLO   near UCLA"), "hello near UCLA");
  assert.equal(stripBilloMention("@Billo"), "");
});

test("direct chats accept untagged requests while groups require a mention", () => {
  for (const text of ["find care near UCLA", "read my receipt", "hello Billo"]) {
    assert.equal(hasBilloMention(text), false, text);
    assert.equal(shouldRespond(text, false), true, text);
    assert.equal(shouldRespond(text, true), false, text);
  }
  assert.equal(shouldRespond("@Billo help", true), true);
  assert.equal(shouldRespond("", false), true); // attachment-only direct messages
  assert.equal(shouldRespond("", true), false);
});
