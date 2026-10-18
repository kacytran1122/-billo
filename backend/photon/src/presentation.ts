export const BILLO_WEBSITE = "https://www.getbillo.us";

/** Native WhatsApp formatting only. Public information link, never a private-case claim. */
export function presentMessage(text: string, channel: string): string {
  if (channel !== "whatsapp_business") return text;
  const clean = text.trim();
  if (!clean) return text;
  const [headline, ...rest] = clean.split("\n");
  const title = headline.length <= 90 && !headline.includes("*") && !headline.startsWith("http")
    ? `*${headline}*` : headline;
  const body = rest.join("\n").trim().replace(/^Total · (\$[\d,.]+)$/gm, "*Total · $1*");
  let result = body ? `${title}\n\n${body}` : title;

  // Link on welcome and useful summaries, not on every progress/STOP/emergency message.
  const summary = /^(?:👋|📍|🧾|💸|✅ Care plan saved)/u.test(headline.replaceAll("*", ""));
  if (summary && !/https?:\/\/(?:www\.)?getbillo\.us(?:[\s/#?]|$)/i.test(result)) {
    result += `\n\nMore about Billo\n${BILLO_WEBSITE}`;
  }
  return result.replace(/\n{3,}/g, "\n\n");
}
