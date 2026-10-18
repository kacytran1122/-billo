import "server-only";

const coreUrl = (process.env.CORE_URL || "http://localhost:8000").replace(/\/$/, "");

export class CoreApiError extends Error {
  constructor(public readonly status: number) {
    super(`Core API returned ${status}`);
    this.name = "CoreApiError";
  }
}

export async function coreRequest(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("x-internal-token", process.env.INTERNAL_TOKEN || "dev-token");
  headers.set("accept", "application/json");
  const response = await fetch(`${coreUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new CoreApiError(response.status);
  return response.json();
}
