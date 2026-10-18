/** Pure chat-routing rules shared by the live bridge and its tests. */
const MENTION_RE = /@billo\b/i;
/** Mentions are optional in direct chats; required to activate Billo in groups. */
export const hasBilloMention = (text: string): boolean => MENTION_RE.test(text);

export const shouldRespond = (text: string, isGroup: boolean): boolean =>
  !isGroup || hasBilloMention(text);

/** Remove every mention before the message reaches the care workflow. */
export const stripBilloMention = (text: string): string =>
  text.replace(/@billo\b/gi, " ").replace(/\s+/g, " ").trim();
