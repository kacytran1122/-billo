import "server-only";

const coreUrl = (process.env.CORE_URL || "http://localhost:8000").replace(/\/$/, "");

export async function coreRequest(path, init = {}) {
  const headers = new Headers(init.headers);
  headers.set("x-internal-token", process.env.INTERNAL_TOKEN || "dev-token");
  headers.set("accept", "application/json");

  const response = await fetch(`${coreUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });

  if (!response.ok) {
    throw new Error(`Core API returned ${response.status}`);
  }
  return response.json();
}
