const limits = {
  query: 160,
  location: 80,
};

function clean(value, fallback, limit) {
  const normalized = typeof value === "string" ? value.trim() : "";
  return (normalized || fallback).slice(0, limit);
}

export function normalizeCareSearch(searchParams) {
  return {
    q: clean(searchParams.get("q"), "routine visit", limits.query),
    near: clean(searchParams.get("near"), "UCLA", limits.location),
  };
}
