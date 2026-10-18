import assert from "node:assert/strict";
import test from "node:test";
import type { Message, Space } from "spectrum-ts";
import { readFileSync } from "node:fs";
import {
  EMERGENCY_CAPTION_PHRASES, handle, hasEmergencyCaption, type HandleDependencies,
} from "../../../backend/photon/src/main.ts";
import type { DocumentAttachment } from "../../../backend/photon/src/documents.ts";

let sequence = 0;

const attachment = (): DocumentAttachment => ({
  type: "attachment",
  name: "bill.png",
  mimeType: "image/png",
  read: async () => new Uint8Array(),
});

const inbound = (text: string, attachments: DocumentAttachment[] = []): Message => ({
  id: `test-message-${++sequence}`,
  direction: "inbound",
  sender: { id: "test-patient" },
  content: {
    type: "group",
    items: [
      { content: { type: "text", text } },
      ...attachments.map(content => ({ content })),
    ],
  },
}) as unknown as Message;

const space = (type: "private" | "group" = "private"): Space => ({
  id: `test-space-${++sequence}`,
  type,
  __platform: "imessage",
  send: async () => undefined,
}) as unknown as Space;

const dependencies = (
  forwarded: Record<string, unknown>[],
  upload: HandleDependencies["upload"],
): HandleDependencies => ({
  core: async () => ({}),
  forward: async payload => { forwarded.push(payload); },
  typing: async () => undefined,
  upload,
});

test("tagged group attachments reach the explicit privacy reply flow without upload", async () => {
  const forwarded: Record<string, unknown>[] = [];
  let uploads = 0, coreRequests = 0;
  const actions = dependencies(
    forwarded,
    async () => {
      uploads += 1;
      throw new Error("group document must never be read or uploaded");
    },
  );
  actions.core = async () => {
    coreRequests += 1;
    throw new Error("group document must never reach Core");
  };
  await handle(space("group"), inbound("@Billo review this bill", [attachment()]), actions);

  assert.equal(uploads, 0);
  assert.equal(coreRequests, 0);
  assert.equal(forwarded.length, 1);
  assert.equal(forwarded[0].is_group, true);
  assert.equal(forwarded[0].text, "review this bill");
  assert.equal(forwarded[0].attachment_url, "");
  assert.equal(forwarded[0].attachment_error, "invalid");
});

test("emergency captions reach Coordinator without waiting on a stalled attachment", async () => {
  const forwarded: Record<string, unknown>[] = [];
  let uploads = 0;
  const stalledUpload: HandleDependencies["upload"] = async () => {
    uploads += 1;
    return await new Promise<string>(() => undefined);
  };

  const completed = await Promise.race([
    handle(space(), inbound("I have chest pain; this is my bill", [attachment()]), dependencies(forwarded, stalledUpload))
      .then(() => true),
    new Promise<boolean>(resolveTimeout => setTimeout(() => resolveTimeout(false), 250)),
  ]);

  assert.equal(completed, true, "the safety caption must not wait for attachment I/O");
  assert.equal(uploads, 0);
  assert.equal(forwarded.length, 1);
  assert.equal(forwarded[0].text, "I have chest pain; this is my bill");
  assert.equal(forwarded[0].attachment_url, "");
  assert.equal(forwarded[0].attachment_error, "safety_deferred");
});

test("ordinary direct-chat attachments retain the existing upload flow", async () => {
  const forwarded: Record<string, unknown>[] = [];
  let uploads = 0;
  await handle(space(), inbound("Please review my receipt", [attachment()]), dependencies(
    forwarded,
    async () => {
      uploads += 1;
      return "file:private-document.png";
    },
  ));

  assert.equal(uploads, 1);
  assert.equal(forwarded.length, 1);
  assert.equal(forwarded[0].is_group, false);
  assert.equal(forwarded[0].attachment_url, "file:private-document.png");
  assert.equal(forwarded[0].attachment_error, "");
});

test("emergency caption matching mirrors explicit negation and contrast behavior", () => {
  assert.equal(hasEmergencyCaption("I have chest pain"), true);
  assert.equal(hasEmergencyCaption("No chest pain and no trouble breathing"), false);
  assert.equal(hasEmergencyCaption("No chest pain, but now I have trouble breathing"), true);
});

test("bridge emergency triggers stay synchronized with the Coordinator rule file", () => {
  const yaml = readFileSync(new URL("../../../backend/rules/red_flags.yaml", import.meta.url), "utf8");
  const configured = [...yaml.matchAll(/^\s*any:\s*\[(.*)\]\s*$/gm)]
    .flatMap(match => JSON.parse(`[${match[1]}]`) as string[]);
  assert.deepEqual([...EMERGENCY_CAPTION_PHRASES], configured);
});
