/** Receipt transport validation. Filenames and declared MIME types are not trusted. */
export const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024;
export const DOCUMENT_TIMEOUT_MS = 20_000;

export class DocumentError extends Error {}

export type DocumentAttachment = {
  type: "attachment";
  name?: string;
  mimeType?: string;
  size?: number;
  read: () => Promise<Buffer | Uint8Array>;
  stream?: () => Promise<ReadableStream<Uint8Array>>;
};

type ParsedInbound = { sender: string; text: string; attachments: DocumentAttachment[] };

/** Follow current content only, never the quoted target of a reply. */
export function parseInboundDocument(message: unknown): ParsedInbound | undefined {
  const incoming = message as { direction?: string; sender?: { id?: string }; content?: unknown } | null;
  if (incoming?.direction !== "inbound" || !incoming.sender?.id) return;
  const texts: string[] = [];
  const attachments: DocumentAttachment[] = [];
  let supported = false;
  const visited = new Set<object>();
  const visit = (value: unknown, depth = 0) => {
    if (!value || typeof value !== "object" || visited.has(value) || depth > 8) return;
    visited.add(value);
    const content = value as { type?: string; text?: unknown; items?: unknown[]; content?: unknown };
    if (content.type === "text") {
      supported = true;
      if (typeof content.text === "string") texts.push(content.text);
    } else if (content.type === "attachment") {
      supported = true;
      attachments.push(content as DocumentAttachment);
    } else if (content.type === "group" && Array.isArray(content.items)) {
      supported = true;
      for (const item of content.items) visit((item as { content?: unknown } | null)?.content, depth + 1);
    } else if (content.type === "reply") {
      visit(content.content, depth + 1);
    }
  };
  visit(incoming.content);
  if (!supported) return;
  return { sender: incoming.sender.id, text: texts.join(" ").trim(), attachments };
}

/** Supported file signatures, including generic-MIME iPhone images and PDFs. */
export function documentMimeType(data: Buffer): string {
  if (data.length >= 3 && data[0] === 0xff && data[1] === 0xd8 && data[2] === 0xff) return "image/jpeg";
  if (data.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return "image/png";
  if (data.length >= 12 && data.toString("ascii", 0, 4) === "RIFF" && data.toString("ascii", 8, 12) === "WEBP") return "image/webp";
  if (data.toString("ascii", 0, 5) === "%PDF-") return "application/pdf";
  if (data.length >= 16 && data.toString("ascii", 4, 8) === "ftyp") {
    const size = data.readUInt32BE(0);
    const brands = [data.toString("ascii", 8, 12)];
    for (let offset = 16; offset + 4 <= Math.min(size, data.length, 256); offset += 4) {
      brands.push(data.toString("ascii", offset, offset + 4));
    }
    if (brands.some(brand => brand === "avif" || brand === "avis")) throw new DocumentError("Unsupported document type");
    if (brands.some(brand => ["heic", "heix", "hevc", "hevx", "heim", "heis", "hevm", "hevs"].includes(brand))) return "image/heic";
    if (brands.some(brand => brand === "mif1" || brand === "msf1")) return "image/heif";
  }
  throw new DocumentError("Unsupported document type");
}

async function boundedRead(attachment: DocumentAttachment, timeoutMs: number): Promise<Buffer> {
  const controller = new AbortController();
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new DocumentError("Attachment download timed out"));
    }, timeoutMs);
  });
  const read = async () => {
    if (typeof attachment.stream !== "function") {
      if (typeof attachment.read !== "function") throw new DocumentError("Attachment could not be downloaded");
      const value = await attachment.read();
      if (!(value instanceof Uint8Array)) throw new DocumentError("Invalid attachment data");
      return Buffer.from(value);
    }
    const stream = await attachment.stream();
    controller.signal.throwIfAborted();
    const reader = stream.getReader();
    const cancel = () => { void reader.cancel().catch(() => {}); };
    controller.signal.addEventListener("abort", cancel, { once: true });
    const chunks: Uint8Array[] = [];
    let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (!(value instanceof Uint8Array)) throw new DocumentError("Invalid attachment data");
        size += value.byteLength;
        if (size > MAX_DOCUMENT_BYTES) throw new DocumentError("Attachment exceeds 10 MB");
        chunks.push(value);
      }
      controller.signal.throwIfAborted();
      return Buffer.concat(chunks);
    } finally {
      controller.signal.removeEventListener("abort", cancel);
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  };
  try { return await Promise.race([read(), timeout]); }
  finally { clearTimeout(timer); }
}

export async function readDocumentAttachment(attachment: DocumentAttachment, timeoutMs = DOCUMENT_TIMEOUT_MS) {
  if (typeof attachment.size === "number" && attachment.size > MAX_DOCUMENT_BYTES) throw new DocumentError("Attachment exceeds 10 MB");
  const data = await boundedRead(attachment, timeoutMs);
  if (!data.length) throw new DocumentError("Attachment is empty");
  if (data.length > MAX_DOCUMENT_BYTES) throw new DocumentError("Attachment exceeds 10 MB");
  return { data, mimeType: documentMimeType(data) };
}

/** Return only a Core-issued local file reference, never an arbitrary remote URL. */
export async function uploadDocument(attachment: DocumentAttachment, options: {
  coreUrl: string; token: string; fetcher?: typeof fetch; timeoutMs?: number;
}): Promise<string> {
  const timeoutMs = options.timeoutMs ?? DOCUMENT_TIMEOUT_MS;
  const { data, mimeType } = await readDocumentAttachment(attachment, timeoutMs);
  const response = await (options.fetcher ?? fetch)(`${options.coreUrl}/files`, {
    method: "POST",
    headers: { "content-type": mimeType, "x-internal-token": options.token },
    body: data,
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) throw new DocumentError(`Document upload failed (${response.status})`);
  const result = await response.json() as { file_url?: unknown };
  if (typeof result.file_url !== "string" || !/^file:[a-zA-Z0-9][a-zA-Z0-9._-]{0,200}$/.test(result.file_url) || result.file_url.includes("..")) {
    throw new DocumentError("Invalid document upload response");
  }
  return result.file_url;
}
