export const BILLO_WEBSITE = "https://www.getbillo.us";
export const BILLO_SCREENS = {
  prices: `${BILLO_WEBSITE}/tools/prices`,
  estimate: `${BILLO_WEBSITE}/tools/estimate`,
  scan: `${BILLO_WEBSITE}/tools/scan`,
  match: `${BILLO_WEBSITE}/tools/match`,
  benefits: `${BILLO_WEBSITE}/tools/benefits`,
} as const;

function relevantScreen(headline: string) {
  if (/^(?:🧾|Document review complete|Receipt organized|Bill organized)/u.test(headline)) return ["Review the organized charges", BILLO_SCREENS.match];
  if (/^(?:💸|Benefit)/u.test(headline)) return ["Review benefit paths", BILLO_SCREENS.benefits];
  if (/^(?:Care plan saved|✅ Care plan saved)/u.test(headline)) return ["Review the saved estimate", BILLO_SCREENS.estimate];
  if (/^📍/u.test(headline)) return ["Compare care", BILLO_SCREENS.prices];
  return ["Explore Billo features", `${BILLO_WEBSITE}/#features`];
}

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
  const summary = /^(?:👋|📍|🧾|💸|(?:✅ )?Care plan saved)/u.test(headline.replaceAll("*", ""));
  if (summary && !/https?:\/\/(?:www\.)?getbillo\.us(?:[\s/#?]|$)/i.test(result)) {
    const [label, url] = relevantScreen(headline.replaceAll("*", ""));
    result += `\n\n${label} (demo)\n${url}`;
  }
  return result.replace(/\n{3,}/g, "\n\n");
}
