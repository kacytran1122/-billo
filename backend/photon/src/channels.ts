export type Channel = "imessage" | "whatsapp_business";

export function configuredChannels(value = "imessage"): Channel[] {
  const channels = [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))];
  if (!channels.length || channels.some((channel) => !["imessage", "whatsapp_business"].includes(channel))) {
    throw new Error("PHOTON_CHANNELS must contain imessage and/or whatsapp_business");
  }
  return channels as Channel[];
}

// Keep existing iMessage case destinations compatible; namespace WhatsApp separately.
export function destinationKey(channel: string, id: string): string {
  return channel === "whatsapp_business" ? `whatsapp_business:${id}` : id;
}

export function destination(value: string): { channel: Channel; id: string } {
  const prefix = "whatsapp_business:";
  return value.startsWith(prefix)
    ? { channel: "whatsapp_business", id: value.slice(prefix.length) }
    : { channel: "imessage", id: value };
}
