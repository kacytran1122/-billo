export const ASI_ONE_URL = "https://asi1.ai/ai/agent1qdral3yqhqaa28czja8ddwf7kzgj4evwmpd39qjz3zuxwc64tucyus67y0z";

/** Photon project assignment verified through the Beta API. A shared line needs assignment first. */
export const IMESSAGE_LINE = "+16282634622";
export const IMESSAGE_URL = `sms:${IMESSAGE_LINE}?body=${encodeURIComponent("Hi Billo")}`;

/** Only publish an operator-configured WhatsApp destination, never a demo number. */
export function whatsappDestination(value: string | undefined): string {
  if (!value?.trim()) return "";
  try {
    const url = new URL(value.trim());
    if (url.protocol !== "https:" || url.username || url.password || url.port) return "";
    if (url.hostname === "wa.me" && /^\/[1-9]\d{7,14}$/.test(url.pathname)) {
      url.searchParams.set("text", "@Billo help");
      return url.toString();
    }
  } catch { /* Incomplete configuration must not become a broken QR. */ }
  return "";
}

export const WHATSAPP_URL = whatsappDestination(process.env.NEXT_PUBLIC_BILLO_WHATSAPP_URL);
