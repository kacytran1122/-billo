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
  const money = (value) => {
    const amount = Number(value);
    return Number.isFinite(amount) ? Math.max(0, amount) : 0;
  };
  return payload.places.slice(0, 3).map((place) => ({
    name: place.name || "Care provider",
    kind: place.kind || "clinic",
    address: place.address || "Address unavailable",
    hours: place.hours || "Call for hours",
    low: money(place.price_low),
    typical: money(place.price_typical),
    source: place.price_source || "posted price",
  }));
}

export function sanitizeSmsAddress(value) {
  const address = String(value || "").trim();
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) return address;
  if (!/^\+?[0-9 ()-]{7,20}$/.test(address)) return "";
  return address.replace(/[ ()-]/g, "");
}

export function buildSmsUrl(line, message = "@Billo help me compare care options") {
  const address = sanitizeSmsAddress(line);
  if (!address) return "#start";
  const separator = /iPhone|iPad|iPod/i.test(globalThis.navigator?.userAgent || "") ? "&" : "?";
  return `sms:${address}${separator}body=${encodeURIComponent(message)}`;
}
