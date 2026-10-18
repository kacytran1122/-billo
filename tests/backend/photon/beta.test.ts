import assert from "node:assert/strict";
import test from "node:test";
import { BetaTransport, contentParts, inboundBeta, type BetaMessage } from "../../../backend/photon/src/beta.ts";

const project = "pho_prj_test";
const message: BetaMessage = {
  id: "pho_msg_test", projectId: project, platform: "imessage", status: "received",
  sentBy: { id: "pho_usr_patient", kind: "person" },
  receivedBy: { id: "pho_usr_billo", kind: "agent" },
  space: { id: "pho_spc_test", kind: "direct", platform: "imessage", participantIds: [] },
  content: { type: "text", text: "hello" },
};
const event = (object = message) => ({ type: "message.received", data: { projectId: project, object } });

test("Beta accepts direct iMessage without requiring a tag", () => {
  assert.equal(inboundBeta(event(), project), message);
});
test("Beta requires an explicit SMS opt-in and respects a SMS-only configuration", () => {
  const sms = { ...message, platform: "sms", space: { ...message.space, platform: "sms" } };
  assert.equal(inboundBeta(event(sms), project), undefined);
  assert.equal(inboundBeta(event(sms), project, ["imessage"]), undefined);
  assert.equal(inboundBeta(event(sms), project, ["sms"]), sms);
  assert.equal(inboundBeta(event(sms), project, ["imessage", "sms"]), sms);
  assert.equal(inboundBeta(event(), project, ["sms"]), undefined);
});
test("Beta rejects mixed-platform snapshots, including when both channels are enabled", () => {
  assert.equal(inboundBeta(event({ ...message, platform: "sms" }), project, ["imessage", "sms"]), undefined);
  assert.equal(inboundBeta(event({ ...message, space: { ...message.space, platform: "sms" } }), project, ["imessage", "sms"]), undefined);
});
test("Beta ignores WhatsApp, wrong project, outbound echoes and delivery receipts", () => {
  assert.equal(inboundBeta(event({ ...message, platform: "whatsapp_business" }), project), undefined);
  assert.equal(inboundBeta(event(), "pho_prj_other"), undefined);
  assert.equal(inboundBeta(event({ ...message, projectId: "pho_prj_other" }), project), undefined);
  assert.equal(inboundBeta(event({ ...message, sentBy: { id: "agent", kind: "agent" } }), project), undefined);
  assert.equal(inboundBeta({ ...event(), type: "message.delivered" }, project), undefined);
});
test("SMS opt-in does not relax project boundaries or accept agent echoes", () => {
  const sms = { ...message, platform: "sms", space: { ...message.space, platform: "sms" } };
  assert.equal(inboundBeta({ ...event(sms), data: { projectId: "pho_prj_other", object: sms } }, project, ["sms"]), undefined);
  assert.equal(inboundBeta(event({ ...sms, projectId: "pho_prj_other" }), project, ["sms"]), undefined);
  assert.equal(inboundBeta(event({ ...sms, sentBy: { id: "pho_usr_agent", kind: "agent" } }), project, ["sms"]), undefined);
  const whatsapp = { ...message, platform: "whatsapp_business", space: { ...message.space, platform: "whatsapp_business" } };
  assert.equal(inboundBeta(event(whatsapp), project, ["whatsapp_business"]), undefined);
});
test("Beta ignores typing indicators, malformed events and non-received messages", () => {
  assert.equal(inboundBeta(event({ ...message, content: { type: "space.typing.update" } }), project), undefined);
  assert.equal(inboundBeta({} as never, project), undefined);
  assert.equal(inboundBeta(event({ ...message, status: "accepted" }), project), undefined);
});
test("Beta preserves an upload caption and every attachment for validation", () => {
  assert.deepEqual(contentParts({ type: "group", parts: [
    { type: "text", text: "unpaid bill" }, { type: "attachment", attachmentId: "pho_att_one" },
    { type: "attachment", attachmentId: "pho_att_two" },
  ] }), { text: "unpaid bill", attachments: ["pho_att_one", "pho_att_two"] });
  assert.deepEqual(contentParts({ type: "attachment", attachmentId: "pho_att_one" }), { text: "", attachments: ["pho_att_one"] });
});
test("Beta rejects stable Spectrum credentials and reports disconnected before subscribing", () => {
  assert.throws(() => new BetaTransport("uuid-project", "old-secret", "/tmp/state"));
  const transport = new BetaTransport(project, "pho_sk_test", "/tmp/state");
  assert.deepEqual(transport.health(), { transport: "photon-beta", connected: false, subscribed: false });
});
test("Beta configuration rejects empty channels and unsupported providers", () => {
  assert.throws(() => new BetaTransport(project, "pho_sk_test", "/tmp/state", []));
  assert.throws(() => new BetaTransport(project, "pho_sk_test", "/tmp/state", ["whatsapp_business"]));
});
test("saved reply routes restore only on their original, enabled platform", async (t) => {
  const transport = new BetaTransport(project, "pho_sk_test", "/tmp/state", ["imessage", "sms"]);
  // Seed an already-restored checkpoint without starting a live socket or reading secrets.
  Object.assign(transport, { state: { projectId: project, cursor: 1, routes: {
    pho_spc_sms: { platform: "sms", senderId: "pho_usr_smsagent", kind: "direct" },
    pho_spc_imessage: { platform: "imessage", senderId: "pho_usr_imessageagent", kind: "direct" },
  } } });
  assert.equal(await transport.getSpace("pho_spc_sms"), undefined);
  assert.equal(await transport.getSpace("pho_spc_sms", "imessage"), undefined);
  assert.equal(await transport.getSpace("pho_spc_imessage", "sms"), undefined);
  assert.equal(await transport.getSpace("invalid", "sms"), undefined);
  const sms = await transport.getSpace("pho_spc_sms", "sms");
  assert.equal(sms?.__platform as string, "sms");
  assert.equal((await transport.getSpace("pho_spc_imessage"))?.__platform, "imessage");
  const requests: unknown[] = [];
  t.mock.method(globalThis, "fetch", async (_url: unknown, options: RequestInit) => {
    requests.push(JSON.parse(String(options.body)));
    return new Response("{}", { status: 200 });
  });
  await sms!.send("Please share your city or ZIP code.");
  assert.deepEqual(requests, [{
    spaceId: "pho_spc_sms", senderId: "pho_usr_smsagent",
    content: { type: "text", format: "plain", text: "Please share your city or ZIP code." },
  }]);
});
test("saved SMS routes remain inaccessible when SMS is disabled", async () => {
  const transport = new BetaTransport(project, "pho_sk_test", "/tmp/state");
  Object.assign(transport, { state: { projectId: project, cursor: 1, routes: {
    pho_spc_sms: { platform: "sms", senderId: "pho_usr_smsagent", kind: "direct" },
  } } });
  assert.equal(await transport.getSpace("pho_spc_sms", "sms"), undefined);
});
