/** Pure chat-routing rules shared by the live bridge and its tests. */
const MENTION_RE = /@billo\b/i;
const PRIVATE_ONLY_WORDS = /\b(bill|invoice|statement|receipt|owe|charged|pay|payment|card|benefit|reimbursement|hsa|fsa|hra|approve|settlement|qr)\b/i;

/** A visible @Billo mention activates Billo in every chat. */
export const hasBilloMention = (text: string): boolean => MENTION_RE.test(text);

/** Remove every mention before the message reaches the care workflow. */
export const stripBilloMention = (text: string): string =>
  text.replace(/@billo\b/gi, " ").replace(/\s+/g, " ").trim();

/** These workflows contain private financial or health-adjacent records. */
export const isPrivateOnlyGroupRequest = (text: string): boolean => PRIVATE_ONLY_WORDS.test(text);
