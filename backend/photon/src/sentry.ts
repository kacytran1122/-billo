/**
 * Privacy-safe Sentry for the Photon bridge. Imported first by main.ts.
 *
 * Mirrors observability/sentry.py: no default PII, no request bodies, no query
 * strings, and phone numbers / emails / amounts are masked in every event, span,
 * breadcrumb and log before anything leaves the process.
 */
import * as Sentry from "@sentry/node";
import { config as loadEnv } from "dotenv";

loadEnv({ path: new URL("../../.env", import.meta.url).pathname });

const env = (k: string, d = "") => (process.env[k] ?? d).trim();

const PATTERNS: [RegExp, string][] = [
  [/[\w.+-]+@[\w-]+\.[\w.-]+/g, "[email]"],
  [/\b\d(?:[ -]?\d){12,18}\b/g, "[card]"],
  [/\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/g, "[date]"],
  [/\+?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b/g, "[phone]"],
  [/\$\s?\d[\d,]*(?:\.\d+)?/g, "[amount]"],
];
const SENSITIVE_KEY = /(?:^|[^a-z0-9])(text|body|phone|handle|sender|email|address|lines|file_url|attachment|token|secret|authorization|cookie)/i;
const SAFE_METRIC_ATTRS = new Set(["agent", "task", "result", "budget", "route", "mode", "action", "reader"]);

export function scrubText(value: string): string {
  return PATTERNS.reduce((v, [re, sub]) => v.replace(re, sub), value);
}

const stripQuery = (url: unknown) => (typeof url === "string" ? url.split("?")[0] : url);

export function scrub<T>(value: T, depth = 0): T {
  if (depth > 12) return "[Filtered]" as T;
  if (typeof value === "string") return scrubText(value) as T;
  if (Array.isArray(value)) return value.map((v) => scrub(v, depth + 1)) as T;
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = SENSITIVE_KEY.test(k) && !["sentry-trace", "baggage", "trace_id", "span_id"].includes(k)
        ? "[Filtered]"
        : scrub(v, depth + 1);
    }
    return out as T;
  }
  return value;
}

function scrubEvent<E extends Sentry.Event>(event: E): E {
  if (event.message) event.message = scrubText(event.message);
  for (const ex of event.exception?.values ?? []) {
    if (ex.value) ex.value = scrubText(ex.value);
    for (const frame of ex.stacktrace?.frames ?? []) delete frame.vars;
  }
  if (event.request) {
    event.request = { method: event.request.method, url: stripQuery(event.request.url) as string };
  }
  if (event.breadcrumbs) event.breadcrumbs = event.breadcrumbs.map((b) => scrubBreadcrumb(b));
  if (event.extra) event.extra = scrub(event.extra);
  for (const span of event.spans ?? []) {
    if (span.description) span.description = scrubText(stripQuery(span.description) as string);
    if (span.data) {
      const data = scrub(span.data) as Record<string, unknown>;
      for (const k of ["url", "http.url", "url.full"]) if (k in data) data[k] = stripQuery(data[k]);
      delete data["http.query"];
      delete data["url.query"];
      span.data = data as typeof span.data;
    }
  }
  delete event.user;
  return event;
}

function scrubBreadcrumb(crumb: Sentry.Breadcrumb): Sentry.Breadcrumb {
  if (crumb.message) crumb.message = scrubText(crumb.message);
  if (crumb.data) {
    const data = scrub(crumb.data) as Record<string, unknown>;
    if ("url" in data) data.url = stripQuery(data.url);
    delete data["http.query"];
    crumb.data = data;
  }
  return crumb;
}

const DSN = env("SENTRY_DSN");
const OWN_SERVICES = [env("CORE_URL", "http://localhost:8000"), env("GATEWAY_URL", "http://localhost:8006")]
  .filter(Boolean)
  .map((u) => u.replace(/\/$/, ""));

if (DSN) {
  Sentry.init({
    dsn: DSN,
    environment: env("SENTRY_ENVIRONMENT", "hackathon"),
    release: env("SENTRY_RELEASE") || undefined,
    serverName: "billo-bridge",
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: {
        request: { allow: ["content-type", "user-agent", "sentry-trace", "baggage"] },
        response: false,
      },
      httpBodies: [],
      urlQueryParams: false,
      graphQL: { document: false, variables: false },
      genAI: { inputs: false, outputs: false },
      databaseQueryData: false,
      queues: false,
      stackFrameVariables: false,
      frameContextLines: 3,
    },
    tracesSampleRate: Number(env("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
    // Static traces keep beforeSendTransaction active, so the final PHI scrubber
    // runs over the complete transaction and every child span before upload.
    traceLifecycle: "static",
    tracePropagationTargets: ["localhost", "127.0.0.1", ...OWN_SERVICES],
    integrations: [
      Sentry.httpIntegration({
        maxRequestBodySize: "none",
        ignoreIncomingRequests: (url) => url.includes("/health"),
      }),
    ],
    beforeSend: (event) => scrubEvent(event),
    beforeSendTransaction: (event) => scrubEvent(event),
    beforeBreadcrumb: (crumb) => scrubBreadcrumb(crumb),
    beforeSendLog: (log) => ({ ...log, message: scrubText(String(log.message)), attributes: scrub(log.attributes) }),
    beforeSendMetric: (metric) => ({
      ...metric,
      attributes: Object.fromEntries(
        Object.entries(metric.attributes ?? {}).filter(([key]) => SAFE_METRIC_ATTRS.has(key) || key.startsWith("sentry.")),
      ),
    }),
  });
  Sentry.setTag("agent", "bridge");
}

/** sentry-trace + baggage for the current span, sent inside the Gateway payload. */
export function traceHeaders(): Record<string, string> {
  if (!DSN) return {};
  const data = Sentry.getTraceData();
  const out: Record<string, string> = {};
  if (data["sentry-trace"]) out["sentry-trace"] = data["sentry-trace"];
  if (data.baggage) out.baggage = data.baggage;
  return out;
}

type ObservedOptions = {
  op: string;
  name: string;
  attributes?: Record<string, string | number | boolean>;
};

/** Span + latency/failure/budget metrics for one bridge task. Never records payloads. */
export function observedSpan<T>(options: ObservedOptions, budgetMs: number, work: () => Promise<T>): Promise<T> {
  return Sentry.startSpan(options, async (span) => {
    const started = performance.now();
    let result = "ok";
    try {
      return await work();
    } catch (error) {
      result = "failed";
      Sentry.metrics.count("billo.task.failed", 1, { attributes: { task: options.name, result } });
      throw error;
    } finally {
      const duration = performance.now() - started;
      const budget = duration > budgetMs ? "exceeded" : "within";
      span.setAttributes({ "task.duration_ms": duration, "task.budget_ms": budgetMs, "task.budget": budget });
      Sentry.metrics.distribution("billo.task.duration", duration, {
        unit: "millisecond",
        attributes: { task: options.name, result, budget },
      });
      if (budget === "exceeded") {
        Sentry.metrics.count("billo.task.slow", 1, { attributes: { task: options.name, budget } });
      }
    }
  });
}

export { Sentry };

