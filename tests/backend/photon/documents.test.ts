import assert from "node:assert/strict";
import test from "node:test";
import {
  DocumentError, MAX_DOCUMENT_BYTES, documentMimeType, parseInboundDocument,
  readDocumentAttachment, uploadDocument, type DocumentAttachment,
} from "../../../backend/photon/src/documents.ts";

const png = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0]);
const pdf = Buffer.from("%PDF-1.7\nsynthetic document\n%%EOF");
const photo = (data = png, mimeType?: string): DocumentAttachment => ({
  type: "attachment", name: "receipt", mimeType, read: async () => data,
});
const inbound = (content: unknown) => ({ direction: "inbound", sender: { id: "pho_usr_patient" }, content });

function isoImage(major: string, ...compatible: string[]) {
  const data = Buffer.alloc(16 + compatible.length * 4);
  data.writeUInt32BE(data.length, 0);
  data.write("ftyp", 4);
  data.write(major, 8);
  compatible.forEach((brand, index) => data.write(brand, 16 + index * 4));
  return data;
}

test("Photon direct attachments reach document parsing without a tag or text", () => {
  const attachment = photo();
  assert.deepEqual(parseInboundDocument(inbound(attachment)), {
    sender: "pho_usr_patient", text: "", attachments: [attachment],
  });
});
test("Photon albums preserve captions and every file instead of silently selecting the first", () => {
  const first = photo();
  const second = photo(pdf);
  const result = parseInboundDocument(inbound({ type: "group", items: [
    { content: { type: "text", text: "paid receipt" } }, { content: first },
    { content: { type: "group", items: [{ content: second }, { content: { type: "text", text: "please review" } }] } },
  ] }));
  assert.equal(result?.text, "paid receipt please review");
  assert.deepEqual(result?.attachments, [first, second]);
});
test("reply parsing processes the new attachment, never a previously quoted document", () => {
  const current = photo();
  const quoted = photo(pdf);
  const result = parseInboundDocument(inbound({ type: "reply", content: current,
    target: { content: quoted } }));
  assert.deepEqual(result?.attachments, [current]);
  assert.equal(result?.text, "");
});
test("outbound messages, reactions and malformed messages do not start OCR", () => {
  assert.equal(parseInboundDocument({ ...inbound(photo()), direction: "outbound" }), undefined);
  assert.equal(parseInboundDocument(inbound({ type: "reaction", emoji: "thumbsup" })), undefined);
  assert.equal(parseInboundDocument(inbound(null)), undefined);
  assert.equal(parseInboundDocument(null), undefined);
  assert.equal(parseInboundDocument({ content: photo() }), undefined);
});
test("cyclic or malformed group entries cannot recurse forever or invent files", () => {
  const content: { type: string; items: unknown[] } = { type: "group", items: [] };
  content.items.push(null, {}, { content });
  assert.deepEqual(parseInboundDocument(inbound(content))?.attachments, []);
});
test("supported image/PDF signatures determine MIME, not phone metadata or a filename", () => {
  assert.equal(documentMimeType(png), "image/png");
  assert.equal(documentMimeType(Buffer.from([0xff, 0xd8, 0xff, 0xe1])), "image/jpeg");
  assert.equal(documentMimeType(Buffer.from("RIFF0000WEBPVP8 ")), "image/webp");
  assert.equal(documentMimeType(pdf), "application/pdf");
  assert.equal(documentMimeType(isoImage("heic", "mif1")), "image/heic");
  assert.equal(documentMimeType(isoImage("mif1", "heix")), "image/heic");
  assert.equal(documentMimeType(isoImage("mif1")), "image/heif");
});
test("SVG, HTML, audio and AVIF are rejected even when labeled as supported images", async () => {
  for (const data of [Buffer.from("<svg xmlns='http://www.w3.org/2000/svg'/>"),
    Buffer.from("<html>not a receipt</html>"), Buffer.from("ID3audio"), isoImage("avif", "mif1")]) {
    await assert.rejects(readDocumentAttachment(photo(data, "image/png")), DocumentError);
  }
});
test("generic, missing and misleading declared MIME types do not discard genuine phone documents", async () => {
  for (const mimeType of [undefined, "", "application/octet-stream", "IMAGE/PNG; charset=binary", "application/pdf"]) {
    const result = await readDocumentAttachment(photo(png, mimeType));
    assert.equal(result.mimeType, "image/png");
    assert.deepEqual(result.data, png);
  }
});
test("empty and oversized fallback reads fail before upload", async () => {
  await assert.rejects(readDocumentAttachment(photo(Buffer.alloc(0))), /empty/);
  await assert.rejects(readDocumentAttachment(photo(Buffer.alloc(MAX_DOCUMENT_BYTES + 1))), /10 MB/);
  await assert.rejects(readDocumentAttachment({ ...photo(), read: async () => "not bytes" as never }), /Invalid attachment data/);
});
test("declared oversized files are rejected without downloading", async () => {
  let read = false;
  await assert.rejects(readDocumentAttachment({ ...photo(), size: MAX_DOCUMENT_BYTES + 1,
    read: async () => { read = true; return png; } }), /10 MB/);
  assert.equal(read, false);
});
test("legacy streamed attachments are bounded and canceled when oversized", async () => {
  let canceled = false;
  const attachment = { ...photo(), stream: async () => new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(Buffer.alloc(MAX_DOCUMENT_BYTES)); controller.enqueue(Buffer.from([1])); },
    cancel() { canceled = true; },
  }) };
  await assert.rejects(readDocumentAttachment(attachment), /10 MB/);
  assert.equal(canceled, true);
});
test("phone streams are preferred over an unbounded read method", async () => {
  let read = false;
  const result = await readDocumentAttachment({ ...photo(),
    read: async () => { read = true; return Buffer.alloc(0); },
    stream: async () => new ReadableStream<Uint8Array>({ start(controller) { controller.enqueue(pdf); controller.close(); } }),
  });
  assert.equal(result.mimeType, "application/pdf");
  assert.equal(read, false);
});
test("stalled SDK reads fail within a bounded timeout", async () => {
  await assert.rejects(readDocumentAttachment({ ...photo(), read: () => new Promise(() => {}) }, 5), /timed out/);
});
test("stalled streams are canceled when the document timeout expires", async () => {
  let canceled = false;
  const attachment = { ...photo(), stream: async () => new ReadableStream<Uint8Array>({ cancel() { canceled = true; } }) };
  await assert.rejects(readDocumentAttachment(attachment, 5), /timed out/);
  assert.equal(canceled, true);
});
test("upload forwards normalized document bytes to Core and preserves only its local file reference", async () => {
  let request: { url: unknown; options?: RequestInit } | undefined;
  const file = await uploadDocument(photo(pdf, "application/octet-stream"), {
    coreUrl: "http://core:8000", token: "test-internal-only",
    fetcher: async (url, options) => { request = { url, options }; return new Response(JSON.stringify({ file_url: "file:abcd.pdf" })); },
  });
  assert.equal(file, "file:abcd.pdf");
  assert.equal(request?.url, "http://core:8000/files");
  assert.equal(request?.options?.method, "POST");
  assert.deepEqual(request?.options?.headers, { "content-type": "application/pdf", "x-internal-token": "test-internal-only" });
  assert.deepEqual(request?.options?.body, pdf);
  assert.ok(request?.options?.signal instanceof AbortSignal);
});
test("unsupported documents never reach Core", async () => {
  let fetched = false;
  await assert.rejects(uploadDocument(photo(Buffer.from("not a receipt")), {
    coreUrl: "http://core:8000", token: "test-internal-only",
    fetcher: async () => { fetched = true; return new Response("{}"); },
  }), DocumentError);
  assert.equal(fetched, false);
});
test("upload errors and invalid references cannot be mistaken for successfully uploaded bills", async () => {
  for (const file_url of [undefined, 5, "", "https://untrusted.invalid/bill.png", "file:../bill.pdf", "file:bad/name.pdf"]) {
    await assert.rejects(uploadDocument(photo(), { coreUrl: "http://core:8000", token: "test-internal-only",
      fetcher: async () => new Response(JSON.stringify({ file_url })),
    }), /Invalid document upload response/);
  }
  await assert.rejects(uploadDocument(photo(), { coreUrl: "http://core:8000", token: "test-internal-only",
    fetcher: async () => new Response("private provider diagnostic", { status: 413 }),
  }), error => error instanceof DocumentError && /413/.test(error.message) && !error.message.includes("private"));
});
