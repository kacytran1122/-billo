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
test("Beta ignores WhatsApp, wrong project, outbound echoes and delivery receipts", () => {
  assert.equal(inboundBeta(event({ ...message, platform: "whatsapp_business" }), project), undefined);
  assert.equal(inboundBeta(event(), "pho_prj_other"), undefined);
  assert.equal(inboundBeta(event({ ...message, projectId: "pho_prj_other" }), project), undefined);
  assert.equal(inboundBeta(event({ ...message, sentBy: { id: "agent", kind: "agent" } }), project), undefined);
  assert.equal(inboundBeta({ ...event(), type: "message.delivered" }, project), undefined);
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
