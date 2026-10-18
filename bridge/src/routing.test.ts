import assert from "node:assert/strict";
import test from "node:test";

import { hasBilloMention, isPrivateOnlyGroupRequest, stripBilloMention } from "./routing.ts";

test("group activation recognizes @Billo case-insensitively", () => {
  assert.equal(hasBilloMention("@Billo find urgent care near UCLA"), true);
  assert.equal(hasBilloMention("hey @BILLO can you help"), true);
  assert.equal(hasBilloMention("Billo can you help"), false);
});

test("mention is removed before private or group routing", () => {
  assert.equal(stripBilloMention("@Billo find care"), "find care");
  assert.equal(stripBilloMention("hello @BILLO   near UCLA"), "hello near UCLA");
  assert.equal(stripBilloMention("@Billo"), "");
});

test("private-only requests are blocked from group processing", () => {
  for (const text of ["read my receipt", "check my HSA benefit", "approve payment", "scan this QR"]) {
    assert.equal(isPrivateOnlyGroupRequest(text), true, text);
  }
  assert.equal(isPrivateOnlyGroupRequest("find urgent care near UCLA"), false);
});
