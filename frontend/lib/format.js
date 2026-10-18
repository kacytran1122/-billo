export function formatMoney(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function normalizePlaces(payload) {
  if (!payload || !Array.isArray(payload.places)) return [];
  return payload.places.slice(0, 3).map((place) => ({
    name: place.name || "Care provider",
    kind: place.kind || "clinic",
    address: place.address || "Address unavailable",
    hours: place.hours || "Call for hours",
    low: Number(place.price_low) || 0,
    typical: Number(place.price_typical) || 0,
    source: place.price_source || "posted price",
  }));
}

export function buildSmsUrl(line, message = "@Billo help me compare care options") {
  if (!line) return "#start";
  const separator = /iPhone|iPad|iPod/i.test(globalThis.navigator?.userAgent || "") ? "&" : "?";
  return `sms:${line}${separator}body=${encodeURIComponent(message)}`;
}
