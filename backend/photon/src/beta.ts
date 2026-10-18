/** Photon 2.0 Beta REST + Socket.IO adapter. No Spectrum credentials on this path. */
import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { io } from "socket.io-client";
import type { Message, Space } from "spectrum-ts";
import type { Channel } from "./channels.ts";
import { DocumentError, MAX_DOCUMENT_BYTES, type DocumentAttachment } from "./documents.ts";

type Content = { type: string; text?: string; attachmentId?: string; parts?: Content[] };
type Peer = { id: string; kind?: string };
type Snapshot = { id: string; kind: string; platform: string; participantIds: string[] };
export type BetaMessage = {
  id: string; projectId: string; status: string; platform: string; content: Content;
  space: Snapshot; sentBy: Peer; receivedBy?: Peer; addressedTo?: Peer;
};
type Delivery = { type: string; data: { projectId: string; object: BetaMessage } };
type Route = { platform: string; senderId: string; kind: string };
type State = { projectId: string; cursor: number; routes: Record<string, Route> };

export function inboundBeta(event: Delivery, projectId: string, channels: readonly Channel[] = ["imessage"]): BetaMessage | undefined {
  const message = event?.data?.object;
  if (event?.type !== "message.received" || event.data.projectId !== projectId ||
      message?.projectId !== projectId || message.status !== "received" ||
      !["imessage", "sms"].includes(message.platform) ||
      !channels.some(channel => channel === message.platform) || message.sentBy?.kind === "agent") return;
  if (!message.id || !message.space?.id || !message.sentBy?.id) return;
  if (message.space.platform !== message.platform) return;
  if (!["text", "attachment", "group"].includes(message.content?.type)) return;
  return message;
}

export function contentParts(content: Content): { text: string; attachments: string[] } {
  const text: string[] = [];
  const attachments: string[] = [];
  const visited = new Set<object>();
  const visit = (part: Content, depth = 0) => {
    if (!part || typeof part !== "object" || visited.has(part) || depth > 8) return;
    visited.add(part);
    if (part.type === "group" && Array.isArray(part.parts)) {
      for (const nested of part.parts) visit(nested, depth + 1);
    } else if (part.type === "text" && typeof part.text === "string") text.push(part.text);
    else if (part.type === "attachment") attachments.push(part.attachmentId ?? "");
  };
  visit(content);
  return { text: text.join(" ").trim(), attachments };
}

export class BetaTransport {
  private state: State;
  private connected = false;
  private subscribed = false;
  private epoch = 0;
  private pending = 0;
  private queue = Promise.resolve();

  constructor(private projectId: string, private apiKey: string, private stateFile: string,
    private channels: readonly Channel[] = ["imessage"]) {
    if (!/^pho_prj_[a-z0-9]+$/.test(projectId) || !apiKey.startsWith("pho_sk_")) {
      throw new Error("Photon Beta requires PHOTON_PROJECT_ID and PHOTON_API_KEY");
    }
    if (!channels.length || channels.some(channel => !["imessage", "sms"].includes(channel))) {
      throw new Error("Photon Beta supports only explicitly configured imessage and sms channels");
    }
    this.channels = [...new Set(channels)];
    this.state = { projectId, cursor: 0, routes: {} };
  }

  health() { return { transport: "photon-beta", connected: this.connected, subscribed: this.subscribed }; }

  private async request(path: string, body?: unknown, key?: string): Promise<Response> {
    const response = await fetch(`https://api.photon.codes/v1/projects/${this.projectId}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        authorization: `Bearer ${this.apiKey}`, "user-agent": "Billo/1.0",
        ...(body === undefined ? {} : { "content-type": "application/json", "idempotency-key": key ?? randomUUID() }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(20_000), redirect: "error",
    });
    if (!response.ok) throw new Error(`Photon Beta request failed (${response.status})`);
    return response;
  }

  private async persist() {
    await mkdir(dirname(this.stateFile), { recursive: true });
    await writeFile(`${this.stateFile}.tmp`, JSON.stringify(this.state), { mode: 0o600 });
    await rename(`${this.stateFile}.tmp`, this.stateFile);
  }

  async getSpace(id: string, channel: Channel = "imessage"): Promise<Space | undefined> {
    if (!/^pho_spc_[a-z0-9]+$/.test(id)) return;
    const route = this.state.routes[id];
    if (!route || route.platform !== channel || !this.channels.includes(channel)) return;
    return this.space(id, route);
  }

  private space(id: string, route: Route, inboundId = ""): Space {
    let sendIndex = 0;
    const send = async (text: string) => {
      const key = inboundId ? createHash("sha256").update(`${inboundId}:${sendIndex++}:${text}`).digest("hex") : randomUUID();
      await this.request("/messages", {
        spaceId: id, senderId: route.senderId, content: { type: "text", format: "plain", text },
      }, key);
    };
    return { id, __platform: route.platform, type: route.kind, send } as unknown as Space;
  }

  private attachment(id: string): DocumentAttachment {
    return {
      // Fetch only after the shared bridge has checked STOP, mentions and album
      // count. Actual bytes, not a possibly generic declared MIME, determine type.
      type: "attachment", mimeType: "application/octet-stream", name: "bill",
      read: async () => {
        if (!/^pho_att_[a-z0-9]+$/.test(id)) throw new DocumentError("Invalid attachment ID");
        const metadata = await (await this.request(`/attachments/${id}`)).json() as { sizeBytes?: number } | null;
        if (typeof metadata?.sizeBytes === "number" && metadata.sizeBytes > MAX_DOCUMENT_BYTES) throw new DocumentError("Attachment exceeds 10 MB");
        const data = await this.request(`/attachments/${id}/content`);
        const chunks: Uint8Array[] = [];
        let size = 0;
        if (!data.body) throw new Error("Empty document");
        for await (const chunk of data.body) {
          size += chunk.length;
          if (size > MAX_DOCUMENT_BYTES) throw new DocumentError("Attachment exceeds 10 MB");
          chunks.push(chunk);
        }
        return Buffer.concat(chunks);
      },
    };
  }

  async start(handler: (space: Space, message: Message) => Promise<void>) {
    try {
      const saved = JSON.parse(await readFile(this.stateFile, "utf8")) as State;
      if (saved.projectId !== this.projectId || !Number.isSafeInteger(saved.cursor) || saved.cursor < 0) throw new Error("Invalid Photon checkpoint");
      this.state = saved;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
    const socket = io("https://api.photon.codes", {
      path: `/v1/projects/${this.projectId}/events/ws`, addTrailingSlash: false,
      transports: ["websocket"], extraHeaders: { Authorization: `Bearer ${this.apiKey}` }, autoConnect: false,
    });
    socket.on("connect", () => {
      this.connected = true;
      socket.timeout(10_000).emit("subscribe", { startSeq: this.state.cursor, apiVersion: "2026-07-01" },
        (error: Error | null, result: { ok: boolean }) => {
          this.subscribed = !error && Boolean(result?.ok);
          if (!this.subscribed) { console.error("[photon-beta] subscription failed"); socket.io.engine.close(); }
          else console.log(`[photon-beta] subscribed; enabled channels: ${this.channels.join(", ")}`);
        });
    });
    socket.on("disconnect", () => { this.connected = false; this.subscribed = false; this.epoch++; });
    socket.on("connect_error", () => console.error("[photon-beta] connection failed; retrying"));
    socket.on("delivery_error", () => { console.error("[photon-beta] delivery failed"); socket.io.engine.close(); });
    socket.on("delivery", (event: Delivery, metadata: { seq: number }) => {
      const generation = this.epoch;
      if (!Number.isSafeInteger(metadata?.seq) || metadata.seq <= 0) { socket.io.engine.close(); return; }
      if (++this.pending > 128) { this.pending--; this.epoch++; socket.io.engine.close(); return; }
      this.queue = this.queue.then(async () => {
        if (generation !== this.epoch || metadata.seq <= this.state.cursor) return;
        const message = inboundBeta(event, this.projectId, this.channels);
        if (message) {
          let receiver = message.receivedBy ?? message.addressedTo;
          if (!receiver || receiver.kind !== "agent") {
            const candidates = await Promise.all(message.space.participantIds.filter(id => id !== message.sentBy.id)
              .map(async id => (await (await this.request(`/users/${id}`)).json()) as Peer));
            receiver = candidates.find(peer => peer.kind === "agent");
          }
          if (!receiver) throw new Error("No managed Photon sender found");
          const route = { platform: message.platform, senderId: receiver.id, kind: message.space.kind };
          this.state.routes[message.space.id] = route;
          await this.persist(); // Save reply route before asynchronous coordinator handoff.
          const space = this.space(message.space.id, route, message.id);
          const parts = contentParts(message.content);
          const textContent = { type: "text", text: parts.text };
          const content = parts.attachments.length ? {
            type: "group", items: [{ content: textContent },
              ...parts.attachments.map(id => ({ content: this.attachment(id) }))],
          } : textContent;
          await handler(space, { id: message.id, direction: "inbound", sender: { id: message.sentBy.id }, content } as unknown as Message);
        }
        const previous = this.state.cursor;
        this.state.cursor = metadata.seq;
        try { await this.persist(); } catch (error) { this.state.cursor = previous; throw error; }
      }).catch(() => {
        console.error("[photon-beta] processing failed; resuming from last successful checkpoint");
        if (generation === this.epoch) { this.epoch++; socket.io.engine.close(); }
      }).finally(() => { this.pending--; });
    });
    socket.connect();
  }
}
