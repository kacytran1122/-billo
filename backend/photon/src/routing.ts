/** Pure chat-routing rules shared by the live bridge and its tests. */
const MENTION_RE = /@billo\b/i;
/** A visible @Billo mention activates Billo in either a private or group chat. */
export const hasBilloMention = (text: string): boolean => MENTION_RE.test(text);

/** Remove every mention before the message reaches the care workflow. */
export const stripBilloMention = (text: string): string =>
  text.replace(/@billo\b/gi, " ").replace(/\s+/g, " ").trim();
