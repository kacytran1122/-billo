export type Channel = "imessage" | "sms" | "whatsapp_business";

export function configuredChannels(value = "imessage"): Channel[] {
  const channels = [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))];
  if (!channels.length || channels.some((channel) => !["imessage", "sms", "whatsapp_business"].includes(channel))) {
    throw new Error("PHOTON_CHANNELS must contain imessage, sms and/or whatsapp_business");
  }
  return channels as Channel[];
}

// Keep existing iMessage case destinations compatible; isolate every other channel.
export function destinationKey(channel: string, id: string): string {
  return channel === "sms" || channel === "whatsapp_business" ? `${channel}:${id}` : id;
}

export function destination(value: string): { channel: Channel; id: string } {
  for (const channel of ["sms", "whatsapp_business"] as const) {
    const prefix = `${channel}:`;
    if (value.startsWith(prefix)) return { channel, id: value.slice(prefix.length) };
  }
  return { channel: "imessage", id: value };
}
