const limits = { query: 160, location: 80 };

function clean(value: string | null, fallback: string, limit: number): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  return (normalized || fallback).slice(0, limit);
}

export function normalizeCareSearch(searchParams: URLSearchParams) {
  return {
    q: clean(searchParams.get("q"), "routine visit", limits.query),
    near: clean(searchParams.get("near"), "UCLA", limits.location),
  };
}
