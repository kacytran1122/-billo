/** Photon 2.0 Beta REST + Socket.IO adapter. No Spectrum credentials on this path. */
import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { io } from "socket.io-client";
import type { Message, Space } from "spectrum-ts";

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
class DocumentError extends Error {}

export function inboundBeta(event: Delivery, projectId: string): BetaMessage | undefined {
  const message = event?.data?.object;
  if (event?.type !== "message.received" || event.data.projectId !== projectId ||
      message?.projectId !== projectId || message.status !== "received" ||
      message.platform !== "imessage" || message.sentBy?.kind === "agent") return;
  if (!message.id || !message.space?.id || !message.sentBy?.id) return;
  if (!["text", "attachment", "group"].includes(message.content?.type)) return;
  return message;
}

export function contentParts(content: Content): { text: string; attachments: string[] } {
  const parts = content.type === "group" ? content.parts ?? [] : [content];
  return {
    text: parts.filter(p => p.type === "text").map(p => p.text ?? "").join(" ").trim(),
    attachments: parts.filter(p => p.type === "attachment" && p.attachmentId).map(p => p.attachmentId!),
  };
}

export class BetaTransport {
  private state: State;
  private connected = false;
  private subscribed = false;
  private epoch = 0;
  private pending = 0;
  private queue = Promise.resolve();

  constructor(private projectId: string, private apiKey: string, private stateFile: string) {
    if (!/^pho_prj_[a-z0-9]+$/.test(projectId) || !apiKey.startsWith("pho_sk_")) {
      throw new Error("Photon Beta requires PHOTON_PROJECT_ID and PHOTON_API_KEY");
    }
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

  async getSpace(id: string): Promise<Space | undefined> {
    if (!/^pho_spc_[a-z0-9]+$/.test(id)) return;
    const route = this.state.routes[id];
    if (!route || route.platform !== "imessage") return;
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
    return { id, __platform: "imessage", type: route.kind, send } as unknown as Space;
  }

  private async attachment(id: string) {
    if (!/^pho_att_[a-z0-9]+$/.test(id)) throw new Error("Invalid attachment ID");
    const metadata = await (await this.request(`/attachments/${id}`)).json() as { contentType: string; sizeBytes: number; filename?: string };
    if (metadata.sizeBytes > 10 * 1024 * 1024) throw new DocumentError("Attachment exceeds 10 MB");
    const mimeType = metadata.contentType;
    if (!mimeType?.startsWith("image/") && mimeType !== "application/pdf") throw new DocumentError("Unsupported document type");
    return {
      type: "attachment", mimeType, name: metadata.filename ?? "bill",
      read: async () => {
        const data = await this.request(`/attachments/${id}/content`);
        const chunks: Uint8Array[] = [];
        let size = 0;
        if (!data.body) throw new Error("Empty document");
        for await (const chunk of data.body) {
          size += chunk.length;
          if (size > 10 * 1024 * 1024) throw new DocumentError("Attachment exceeds 10 MB");
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
          else console.log("[photon-beta] subscribed; iMessage only");
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
        const message = inboundBeta(event, this.projectId);
        if (message) {
          let receiver = message.receivedBy ?? message.addressedTo;
          if (!receiver || receiver.kind !== "agent") {
            const candidates = await Promise.all(message.space.participantIds.filter(id => id !== message.sentBy.id)
              .map(async id => (await (await this.request(`/users/${id}`)).json()) as Peer));
            receiver = candidates.find(peer => peer.kind === "agent");
          }
          if (!receiver) throw new Error("No managed iMessage sender found");
          const route = { platform: "imessage", senderId: receiver.id, kind: message.space.kind };
          this.state.routes[message.space.id] = route;
          await this.persist(); // Save reply route before asynchronous coordinator handoff.
          const space = this.space(message.space.id, route, message.id);
          const parts = contentParts(message.content);
          if (parts.attachments.length > 1) {
            await space.send("Please send one bill or receipt at a time so I can review every document accurately.");
          } else {
            try {
              const attachment = parts.attachments[0] ? await this.attachment(parts.attachments[0]) : undefined;
              const textContent = { type: "text", text: parts.text };
              const content = attachment ? { type: "group", items: [{ content: textContent }, { content: attachment }] } : textContent;
              await handler(space, { id: message.id, direction: "inbound", sender: { id: message.sentBy.id }, content } as unknown as Message);
            } catch (error) {
              if (!(error instanceof DocumentError)) throw error;
              await space.send("Please send one clear bill or receipt as an image or PDF under 10 MB. That file could not be processed; no payment was approved.");
            }
          }
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
