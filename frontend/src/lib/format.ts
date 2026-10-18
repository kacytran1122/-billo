export function formatMoney(value: unknown): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

type RawPlace = {
  name?: unknown;
  kind?: unknown;
  address?: unknown;
  hours?: unknown;
  price_low?: unknown;
  price_typical?: unknown;
  price_source?: unknown;
};

export function normalizePlaces(payload: unknown) {
  if (!payload || typeof payload !== "object" || !Array.isArray((payload as { places?: unknown }).places)) return [];
  const money = (value: unknown) => {
    const amount = Number(value);
    return Number.isFinite(amount) ? Math.max(0, amount) : 0;
  };
  return ((payload as { places: RawPlace[] }).places).slice(0, 3).map((place) => ({
    name: typeof place.name === "string" && place.name ? place.name : "Care provider",
    kind: typeof place.kind === "string" && place.kind ? place.kind : "clinic",
    address: typeof place.address === "string" && place.address ? place.address : "Address unavailable",
    hours: typeof place.hours === "string" && place.hours ? place.hours : "Call for hours",
    low: money(place.price_low),
    typical: money(place.price_typical),
    source: typeof place.price_source === "string" && place.price_source ? place.price_source : "posted price",
  }));
}

export function sanitizeSmsAddress(value: unknown): string {
  const address = String(value || "").trim();
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) return address;
  if (!/^\+?[0-9 ()-]{7,20}$/.test(address)) return "";
  return address.replace(/[ ()-]/g, "");
}

export function buildSmsUrl(line: unknown, message = "@Billo help me compare care options"): string {
  const address = sanitizeSmsAddress(line);
  if (!address) return "#start";
  return `sms:${address}?body=${encodeURIComponent(message)}`;
}
