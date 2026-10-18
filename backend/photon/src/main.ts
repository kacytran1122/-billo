/**
 * Billo Spectrum Bridge (Photon iMessage).
 *
 * iMessage -> Photon Spectrum -> THIS BRIDGE -> POST {GATEWAY}/imessage -> Coordinator (Fetch.ai)
 * Coordinator -> Gateway -> POST {BRIDGE}/send -> THIS BRIDGE -> Spectrum -> iMessage
 *
 * The 7 bridge responsibilities:
 *  1 STOP handler                (same result every time per message id; typing dots)
 *  2 Mention filter              (only group chats require @Billo)
 *  3 Chat router                 (private and group chats use the same workflow)
 *  4 Receipt/final bill upload    (attachments forwarded to the After-Care Organizer)
 *  5 Approve                     (patient's own tagged message in the chat)
 *  6 Billo texts first           (the Coordinator's 30-min check arrives via /send)
 *  7 Phone numbers masked        (we only ever log and forward a hash)
 *
 * Spectrum usage follows News Next Door (a past Photon winner), spectrum-ts 12.10.1.
 */
import { observedSpan, scrubText, Sentry, traceHeaders } from "./sentry.ts"; // first: Sentry must start before anything else
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import type { Message, Space } from "spectrum-ts";
import { config as loadEnv } from "dotenv";
import { hasBilloMention, shouldRespond, stripBilloMention } from "./routing.ts";
import { configuredChannels, destination, destinationKey, type Channel } from "./channels.ts";
import { presentMessage } from "./presentation.ts";
import { BetaTransport } from "./beta.ts";
import { parseInboundDocument, uploadDocument, type DocumentAttachment } from "./documents.ts";

loadEnv({ path: new URL("../../.env", import.meta.url).pathname });

const env = (k: string, d = "") => (process.env[k] ?? d).trim();
const CORE = env("CORE_URL", "http://localhost:8000");
const GATEWAY = env("GATEWAY_URL", "http://localhost:8006"); // the iMessage Gateway uAgent REST port
const TOKEN = env("INTERNAL_TOKEN", "dev-token");
const PORT = Number(env("BRIDGE_PORT", "3000"));
const hashHandle = (h: string) => createHash("sha256").update(`${TOKEN}:${h}`).digest("hex").slice(0, 16);
const mask = (h: string) => (h.length > 4 ? `***${h.slice(-4)}` : "***");

const spaces = new Map<string, Space>();
const seen = new Set<string>(); // idempotency: provider message ids we already handled
const typingTimers = new Map<string, NodeJS.Timeout>();

async function core(path: string, body?: unknown) {
  const r = await fetch(`${CORE}${path}`, {
    method: body ? "POST" : "GET",
    headers: { "content-type": "application/json", "x-internal-token": TOKEN },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15_000),
  });
  if (!r.ok) throw new Error(`Core request failed (${r.status})`);
  return r.json() as Promise<Record<string, string>>;
}

async function forward(payload: Record<string, unknown>) {
  const r = await observedSpan({ op: "bridge.forward", name: "gateway-forward" }, 2000, () =>
    fetch(`${GATEWAY}/imessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      // the trace rides inside the body: the Gateway is a uAgents REST handler and cannot read headers
      body: JSON.stringify({ token: TOKEN, ...payload, trace: traceHeaders() }),
      signal: AbortSignal.timeout(15_000),
    }),
  );
  if (!r.ok) {
    console.error("[bridge] gateway refused", r.status);
    Sentry.withScope((scope) => {
      scope.setTag("check", "workflow");
      Sentry.captureMessage(`gateway refused inbound message (${r.status})`, "error");
    });
    throw new Error(`Gateway refused inbound message (${r.status})`);
  }
  const acknowledgement = await r.json() as { ok?: boolean };
  if (acknowledgement.ok !== true) throw new Error("Gateway did not accept inbound message");
}

async function typing(space: Space, on: boolean) {
  const t = space as unknown as { startTyping?: () => Promise<void>; stopTyping?: () => Promise<void> };
  await (on ? t.startTyping?.() : t.stopTyping?.())?.catch(() => {});
  if (on) {
    clearTimeout(typingTimers.get(space.id));
    typingTimers.set(space.id, setTimeout(() => void typing(space, false), 20_000)); // never type forever
  }
}

/** Normalize phone documents and upload within size/time limits before extraction. */
async function upload(att: DocumentAttachment): Promise<string> {
  return observedSpan({ op: "bridge.upload", name: "bill-upload" }, 10000, async () => {
    try {
      return await uploadDocument(att, { coreUrl: CORE, token: TOKEN });
    } catch {
      Sentry.withScope((scope) => {
        scope.setTag("check", "bill_reader");
        // SDK/network errors may contain private URLs. Record only a safe diagnostic.
        Sentry.captureMessage("bill attachment could not be uploaded", "warning");
      });
      return "";
    }
  });
}

async function handle(space: Space, message: Message) {
  const messageKey = `${space.__platform}:${space.id}:${message.id}`;
  if (seen.has(messageKey)) return; // provider IDs need not be unique across channels
  if (seen.size > 5000) seen.clear();

  const ev = parseInboundDocument(message);
  if (!ev) return;
  const spaceKey = destinationKey(space.__platform, space.id);
  spaces.set(spaceKey, space);
  const isGroup = (space as unknown as { type?: string }).type === "group";
  const handleHash = hashHandle(destinationKey(space.__platform, ev.sender));
  const rawText = ev.text.trim();
  const text = stripBilloMention(rawText);
  const rawUpper = text.toUpperCase();
  const tagged = hasBilloMention(rawText);
  const chatKind = isGroup ? "group" : "private";
  const hasAttachments = ev.attachments.length > 0;
  Sentry.getActiveSpan()?.setAttributes({ "chat.group": isGroup, "chat.has_file": hasAttachments });

  // Transport-level receipt without logging message content or a full sender identifier.
  console.log(
    `[bridge] inbound ${chatKind} from ${mask(ev.sender)} (${rawText.length} chars${hasAttachments ? ", attachment" : ""}, tagged=${tagged})`,
  );

  // STOP is always available as a universal opt-out, with or without a mention.
  if (["STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"].includes(rawUpper)) {
    await core("/link/stop", { handle_hash: handleHash });
    // Cancel the coordinator's direct-chat reminders too, even without an ASI link code.
    await forward({ handle_hash: handleHash, space_id: spaceKey, text: "STOP", is_group: isGroup, message_id: message.id });
    seen.add(messageKey);
    return;
  }

  // Direct chats accept plain messages and attachments. Unaddressed group content stays ignored.
  if (!shouldRespond(rawText, isGroup)) return;

  console.log(`[bridge] accepted ${chatKind} request (${text.length} workflow chars)`);
  if (!text && !hasAttachments) {
    await space.send(presentMessage("👋 Meet Billo\n\nMake every care dollar count.\n\nTell me what happened, or attach a bill or receipt.\nTry: help", space.__platform));
    seen.add(messageKey);
    return;
  }
  await typing(space, true);
  const attachmentUrl = ev.attachments.length === 1 ? await upload(ev.attachments[0]) : "";
  const attachmentError = ev.attachments.length > 1 ? "multiple" : hasAttachments && !attachmentUrl ? "invalid" : "";
  // Keep the caption so the coordinator can emergency-screen it first. An explicit
  // attachment error prevents care/payment actions from using a missing document.
  await forward({
    handle_hash: handleHash,
    space_id: spaceKey,
    text,
    is_group: isGroup,
    attachment_url: attachmentUrl,
    attachment_error: attachmentError,
    message_id: message.id,
  });
  seen.add(messageKey);
}

/** The legacy SDK is large. Do not load it in the Photon 2.0 process. */
async function legacyTransport(channels: Channel[]) {
  if (channels.includes("sms")) throw new Error("Photon SMS requires PHOTON_API_VERSION=beta");
  const [{ Spectrum }, { imessage }, { whatsappBusiness }] = await Promise.all([
    import("spectrum-ts"), import("spectrum-ts/providers/imessage"), import("spectrum-ts/providers/whatsapp-business"),
  ]);
  const app = await Spectrum({
    projectId: env("SPECTRUM_PROJECT_ID"), projectSecret: env("SPECTRUM_PROJECT_SECRET"),
    providers: channels.map(channel => channel === "imessage" ? imessage.config() : whatsappBusiness.config()),
    options: { flattenGroups: true },
  });
  return {
    messages: app.messages,
    getSpace: (channel: Channel, id: string) => channels.includes(channel)
      ? (channel === "whatsapp_business" ? whatsappBusiness(app) : imessage(app)).space.get(id).catch(() => undefined)
      : Promise.resolve(undefined),
  };
}

async function main() {
  const channels = configuredChannels(env("PHOTON_CHANNELS", "imessage"));
  const beta = env("PHOTON_API_VERSION") === "beta" ? new BetaTransport(
    env("PHOTON_PROJECT_ID"), env("PHOTON_API_KEY"), env("PHOTON_STATE_FILE", "/data/photon-beta.json"),
    channels,
  ) : undefined;
  const legacy = beta ? undefined : await legacyTransport(channels);

  // ---- outbound: Gateway -> /send -> iMessage ----
  createServer(async (req, res) => {
    try {
    if (req.method === "GET" && req.url === "/health") {
      const state = beta?.health();
      const ready = !beta || Boolean(state?.connected && state?.subscribed);
      res.statusCode = ready ? 200 : 503;
      res.setHeader("content-type", "application/json");
      return void res.end(JSON.stringify({ ok: ready, ...state }));
    }
    if (req.method !== "POST" || req.url !== "/send") return void res.writeHead(404).end();
    if (req.headers["x-internal-token"] !== TOKEN) return void res.writeHead(401).end();
    let body = "";
    for await (const chunk of req) {
      body += chunk;
      if (body.length > 65536) return void res.writeHead(413).end();
    }
    const { space_id, text } = JSON.parse(body) as { space_id: string; text: string };
    if (typeof space_id !== "string" || typeof text !== "string" || !text.trim()) return void res.writeHead(400).end();
    const target = destination(space_id);
    if (!channels.includes(target.channel)) return void res.writeHead(404).end();
    const cached = spaces.get(space_id);
    const space = cached?.__platform === target.channel ? cached
      : (beta ? await beta.getSpace(target.id, target.channel) : await legacy?.getSpace(target.channel, target.id));
    if (!space || space.__platform !== target.channel) return void res.writeHead(404).end("unknown space");
    await typing(space, false);
    try {
      // the http integration already continued the Gateway's trace for this request
      await observedSpan({ op: "bridge.outbound", name: `${target.channel}-send` }, 3000, () => space.send(presentMessage(text, target.channel)));
      res.end(JSON.stringify({ ok: true }));
    } catch (e) {
      Sentry.withScope((scope) => {
        scope.setTag("check", "workflow");
        Sentry.captureException(e);
      });
      res.writeHead(502).end(JSON.stringify({ ok: false }));
    }
    } catch {
      if (!res.headersSent) res.writeHead(400);
      res.end(JSON.stringify({ ok: false }));
    }
  }).listen(PORT, () => console.log(`[bridge] /send listening on :${PORT}`));

  console.log(`[bridge] listening for ${channels.join(", ")}...`);
  if (beta) {
    await beta.start((space, message) => Sentry.withIsolationScope(() =>
      Sentry.startSpan({ op: "bridge.inbound", name: `${space.__platform} inbound`, forceTransaction: true }, () => handle(space, message))));
    return;
  }
  for await (const [space, message] of legacy!.messages) {
    // one isolation scope + one root span per inbound iMessage: the start of the case trace
    void Sentry.withIsolationScope(() =>
      Sentry.startSpan({ op: "bridge.inbound", name: "imessage inbound", forceTransaction: true }, () =>
        handle(space, message).catch((e) => {
          console.error("[bridge] handler error", e instanceof Error ? e.name : "unknown");
          Sentry.captureException(e);
        }),
      ),
    );
  }
}

main().catch(async (e) => {
  console.error("[bridge] fatal", e instanceof Error ? `${e.name}: ${scrubText(e.message)}` : "unknown");
  Sentry.captureException(e);
  await Sentry.flush(2000);
  process.exit(1);
});
