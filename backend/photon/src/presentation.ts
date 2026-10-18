export const BILLO_WEBSITE = "https://www.getbillo.us";
export const BILLO_SCREENS = {
  prices: `${BILLO_WEBSITE}/tools/prices`,
  estimate: `${BILLO_WEBSITE}/tools/estimate`,
  scan: `${BILLO_WEBSITE}/tools/scan`,
  match: `${BILLO_WEBSITE}/tools/match`,
  benefits: `${BILLO_WEBSITE}/tools/benefits`,
} as const;

/** Native WhatsApp formatting only; screen selection belongs to the Coordinator. */
export function presentMessage(text: string, channel: string): string {
  if (channel !== "whatsapp_business") return text;
  const clean = text.trim();
  if (!clean) return text;
  const [headline, ...rest] = clean.split("\n");
  const title = headline.length <= 90 && !headline.includes("*") && !headline.startsWith("http")
    ? `*${headline}*` : headline;
  const body = rest.join("\n").trim().replace(/^Total · (\$[\d,.]+)$/gm, "*Total · $1*");
  const result = body ? `${title}\n\n${body}` : title;
  return result.replace(/\n{3,}/g, "\n\n");
}
