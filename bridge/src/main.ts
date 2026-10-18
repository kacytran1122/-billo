/**
 * Billo Spectrum Bridge (Photon iMessage).
 *
 * iMessage -> Photon Spectrum -> THIS BRIDGE -> POST {GATEWAY}/imessage -> Coordinator (Fetch.ai)
 * Coordinator -> Gateway -> POST {BRIDGE}/send -> THIS BRIDGE -> Spectrum -> iMessage
 *
 * The 7 bridge responsibilities:
 *  1 Code + STOP + HELP handler  (same result every time per message id; typing dots)
 *  2 @Billo filter               (groups: reply only when someone writes @Billo)
 *  3 Privacy router              (bills, payments, approvals: private chat only)
 *  4 Receipt/final bill upload    (attachments forwarded to the After-Care Organizer)
 *  5 Approve                     (patient's own message in the private chat)
 *  6 Billo texts first           (the Coordinator's 30-min check arrives via /send)
 *  7 Phone numbers masked        (we only ever log and forward a hash)
 *
 * Spectrum usage follows News Next Door (a past Photon winner), spectrum-ts 12.10.1.
 */
import { Sentry, traceHeaders } from "./sentry.ts"; // first: Sentry must start before anything else
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { Spectrum, type Message, type Space } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";
import { config as loadEnv } from "dotenv";

loadEnv({ path: new URL("../../.env", import.meta.url).pathname });

const env = (k: string, d = "") => (process.env[k] ?? d).trim();
const CORE = env("CORE_URL", "http://localhost:8000");
const GATEWAY = env("GATEWAY_URL", "http://localhost:8006"); // the iMessage Gateway uAgent REST port
const TOKEN = env("INTERNAL_TOKEN", "dev-token");
const PORT = Number(env("BRIDGE_PORT", "3000"));
const CODE_RE = /\bBILLO-\d{4}\b/i;
const MENTION_RE = /@billo\b/i;
const BILL_WORDS = /\b(bill|invoice|statement|owe|charged|pay|card)\b/i;

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
  });
  return r.json() as Promise<Record<string, string>>;
}

async function forward(payload: Record<string, unknown>) {
  const r = await fetch(`${GATEWAY}/imessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    // the trace rides inside the body: the Gateway is a uAgents REST handler and cannot read headers
    body: JSON.stringify({ token: TOKEN, ...payload, trace: traceHeaders() }),
  });
  if (!r.ok) {
    console.error("[bridge] gateway refused", r.status);
    Sentry.withScope((scope) => {
      scope.setTag("check", "workflow");
      Sentry.captureMessage(`gateway refused inbound message (${r.status})`, "error");
    });
  }
}

async function typing(space: Space, on: boolean) {
  const t = space as unknown as { startTyping?: () => Promise<void>; stopTyping?: () => Promise<void> };
  await (on ? t.startTyping?.() : t.stopTyping?.())?.catch(() => {});
  if (on) {
    clearTimeout(typingTimers.get(space.id));
    typingTimers.set(space.id, setTimeout(() => void typing(space, false), 20_000)); // never type forever
  }
}

type Att = { type: "attachment"; name: string; mimeType: string; read: () => Promise<Buffer> };
type Content = { type: string; text?: string; items?: { content: Content }[] };

/** Turn a Spectrum message into {sender, text, attachment}. Returns undefined for things we ignore. */
function parse(message: Message): { sender: string; text: string; att?: Att } | undefined {
  if (message.direction !== "inbound") return undefined;
  const sender = message.sender?.id;
  if (!sender) return undefined;
  const c = message.content as unknown as Content;
  if (c.type === "text") return { sender, text: String(c.text ?? "") };
  if (c.type === "attachment") return { sender, text: "", att: c as unknown as Att };
  if (c.type === "group") {
    const items = c.items ?? [];
    const text = items.map((i) => (i.content.type === "text" ? String(i.content.text) : "")).join(" ").trim();
    const att = items.find((i) => i.content.type === "attachment")?.content as unknown as Att | undefined;
    return { sender, text, att };
  }
  console.log(`[bridge] ignored content type ${c.type}`);
  return undefined;
}

/** Upload a receipt/final-bill image to the Core API for immediate extraction. */
async function upload(att: Att): Promise<string> {
  if (!att.mimeType.startsWith("image/") && att.mimeType !== "application/pdf") return "";
  return Sentry.startSpan({ op: "bridge.upload", name: "bill photo -> core", attributes: { "file.mime": att.mimeType } }, async (span) => {
    const buf = await att.read();
    span.setAttribute("file.bytes", buf.length);
    const r = await fetch(`${CORE}/files`, {
      method: "POST",
      headers: { "content-type": att.mimeType, "x-internal-token": TOKEN },
      body: buf,
    });
    if (!r.ok) {
      Sentry.withScope((scope) => {
        scope.setTag("check", "bill_reader");
        Sentry.captureMessage(`bill upload failed (${r.status})`, "error");
      });
      return "";
    }
    return ((await r.json()) as { file_url: string }).file_url;
  });
}

async function handle(space: Space, message: Message) {
  if (seen.has(message.id)) return; // same result every time: a resent message never runs twice
  seen.add(message.id);
  if (seen.size > 5000) seen.clear();

  const ev = parse(message);
  if (!ev) return;
  spaces.set(space.id, space);
  const isGroup = (space as unknown as { type?: string }).type === "group";
  const handleHash = hashHandle(ev.sender);
  const text = ev.text.trim();
  Sentry.getActiveSpan()?.setAttributes({ "chat.group": isGroup, "chat.has_file": Boolean(ev.att) });

  // ---- 2. @Billo filter + 3. privacy router (groups) ----
  if (isGroup) {
    if (!MENTION_RE.test(text)) return; // never read (or log) the rest of the group's chat
    console.log(`[bridge] group mention from ${mask(ev.sender)} (${text.length} chars)`);
    if (ev.att || BILL_WORDS.test(text)) { // a bill in a group is never read
      await space.send("Bills and payments are private. Please send them to me in a private chat.");
      return;
    }
    await typing(space, true);
    await forward({ handle_hash: handleHash, space_id: space.id, text: text.replace(MENTION_RE, "").trim(), is_group: true, message_id: message.id });
    return;
  }

  console.log(`[bridge] dm from ${mask(ev.sender)} (${text.length} chars${ev.att ? ", attachment" : ""})`);

  // ---- 1. STOP / HELP / follow code (private chat) ----
  const upper = text.toUpperCase();
  if (["STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"].includes(upper)) {
    await core("/link/stop", { handle_hash: handleHash });
    await space.send("You are unsubscribed. Billo will not text you again. Reply START to come back.");
    return;
  }
  if (upper === "HELP") {
    await space.send("Billo checks medical bills and finds fair prices. Send a photo of a bill, or tell me what happened. Text STOP to stop. In an emergency call 911.");
    return;
  }
  let caseId = "";
  const code = text.match(CODE_RE)?.[0];
  if (code) {
    const res = await core("/link/claim", { code, handle_hash: handleHash, space_id: space.id });
    if (res.status === "expired") return void (await space.send("That code expired. Ask Billo in ASI:One for a new one."));
    if (res.status !== "linked") return void (await space.send("I do not know that code. Please check it and try again."));
    caseId = res.case_id;
    await space.send("Linked. Your case continues here. You can text me what happens at your visit, and send your bill photo when it comes.");
  } else {
    caseId = (await core(`/link/resolve?handle_hash=${handleHash}`)).case_id ?? "";
  }

  // ---- 4/5. everything else goes to the agents ----
  await typing(space, true);
  await forward({ handle_hash: handleHash, space_id: space.id, text: code ? "" : text, is_group: false, case_id: caseId, attachment_url: ev.att ? await upload(ev.att) : "", message_id: message.id });
}

async function main() {
  const app = await Spectrum({
    projectId: env("SPECTRUM_PROJECT_ID"),
    projectSecret: env("SPECTRUM_PROJECT_SECRET"),
    providers: [imessage.config()],
    options: { flattenGroups: true },
  });

  // ---- outbound: Gateway -> /send -> iMessage ----
  createServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/health") return void res.end(JSON.stringify({ ok: true }));
    if (req.method !== "POST" || req.url !== "/send") return void res.writeHead(404).end();
    if (req.headers["x-internal-token"] !== TOKEN) return void res.writeHead(401).end();
    let body = "";
    for await (const chunk of req) body += chunk;
    const { space_id, text } = JSON.parse(body) as { space_id: string; text: string };
    const space = spaces.get(space_id) ?? (await imessage(app).space.get(space_id).catch(() => undefined));
    if (!space) return void res.writeHead(404).end("unknown space");
    await typing(space, false);
    try {
      // the http integration already continued the Gateway's trace for this request
      await Sentry.startSpan({ op: "bridge.outbound", name: "send iMessage" }, () => space.send(text));
      res.end(JSON.stringify({ ok: true }));
    } catch (e) {
      Sentry.withScope((scope) => {
        scope.setTag("check", "workflow");
        Sentry.captureException(e);
      });
      res.writeHead(502).end(JSON.stringify({ ok: false }));
    }
  }).listen(PORT, () => console.log(`[bridge] /send listening on :${PORT}`));

  console.log("[bridge] listening for iMessage...");
  for await (const [space, message] of app.messages) {
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
  console.error("[bridge] fatal", e instanceof Error ? e.name : "unknown");
  Sentry.captureException(e);
  await Sentry.flush(2000);
  process.exit(1);
});
