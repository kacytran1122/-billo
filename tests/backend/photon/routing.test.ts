import assert from "node:assert/strict";
import test from "node:test";

import { hasBilloMention, stripBilloMention } from "../../../backend/photon/src/routing.ts";

test("chat activation recognizes @Billo case-insensitively", () => {
  assert.equal(hasBilloMention("@Billo find urgent care near UCLA"), true);
  assert.equal(hasBilloMention("hey @BILLO can you help"), true);
  assert.equal(hasBilloMention("Billo can you help"), false);
});

test("mention is removed before group routing", () => {
  assert.equal(stripBilloMention("@Billo find care"), "find care");
  assert.equal(stripBilloMention("hello @BILLO   near UCLA"), "hello near UCLA");
  assert.equal(stripBilloMention("@Billo"), "");
});

test("untagged group text does not activate Billo", () => {
  for (const text of ["find care near UCLA", "read my receipt", "hello Billo"]) {
    assert.equal(hasBilloMention(text), false, text);
  }
});
