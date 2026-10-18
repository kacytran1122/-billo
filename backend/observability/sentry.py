"""Privacy-safe Sentry for every Billo service (Core API and all agents).

One module, one policy. Rule 5 in AGENTS.md: no health data and no raw phone
numbers ever leave for Sentry. This file enforces that in four layers:

1. ``SAFE_DATA_COLLECTION``: the SDK never collects request/response bodies,
   query strings, cookies, LLM prompts/outputs, SQL parameters or stack-frame
   local variables in the first place.
2. ``scrub_event``: every event, transaction, span, log and breadcrumb is walked
   recursively. Values under sensitive keys are dropped, and phone numbers,
   emails, dates, card-like numbers and dollar amounts are masked in free text.
3. Metrics only keep attributes from ``SAFE_METRIC_ATTRS``.
4. Case IDs are only ever sent as a keyed hash (``case_hash``).

Usage:
    from observability.sentry import init_sentry
    init_sentry("core")
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import subprocess
import time
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Callable, Iterator

import sentry_sdk

FILTERED = "[Filtered]"

# Things that look like personal or health data inside free text.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\b\d(?:[ -]?\d){12,18}\b"), "[card]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ssn]"),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"), "[date]"),
    (re.compile(r"\+?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"), "[phone]"),
    (re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?"), "[amount]"),
]

# Keys whose values are never sent, at any depth (substring, case-insensitive).
# These are the fields that carry symptoms, bill contents or identity.
SENSITIVE_KEYS = (
    "text", "message_text", "patient_text", "symptom", "lines", "line_items", "charges",
    "diagnosis", "description_raw", "body", "data_raw", "file_url", "attachment",
    "phone", "handle", "sender", "email", "name_full", "first_name", "last_name",
    "address", "dob", "birth", "member", "insurance_id", "policy", "ssn",
    "card", "pan", "cvv", "token", "secret", "password", "authorization", "cookie",
)
# Keys that look sensitive by substring but are safe identifiers we need.
SAFE_KEYS = frozenset({
    "trace_id", "span_id", "parent_span_id", "sentry-trace", "baggage", "case", "case_hash",
    "agent", "check", "op", "status", "reader", "stage", "channel", "environment",
    "release", "server_name", "transaction", "monitor_slug", "check_in_id", "medic.action",
    "settlement.result", "http.method", "http.status_code", "http.route", "route",
    "thread.id", "thread.name",
})

# Context blocks with SDK-generated identifiers that must survive untouched.
_PASSTHROUGH_CONTEXTS = ("trace", "runtime", "os", "device", "monitor", "profile", "app")

SAFE_DATA_COLLECTION: dict[str, Any] = {
    "user_info": False,
    "cookies": {"mode": "off"},
    "http_headers": {"request": {"mode": "denylist"}},
    "http_bodies": [],                          # never request/response bodies (bills!)
    "url_query_params": {"mode": "off"},        # /care/search?q=<symptoms>
    "graphql": {"document": False, "variables": False},
    "gen_ai": {"inputs": False, "outputs": False},  # vision fallback sees bill images
    "database_query_data": False,               # SQL params carry prices and case ids
    "stack_frame_variables": False,             # locals hold bill lines and texts
    "frame_context_lines": 3,
}

# Only these metric attributes are kept; everything else is dropped.
SAFE_METRIC_ATTRS = frozenset({
    "agent", "check", "reader", "stage", "channel", "result", "action", "route", "mode",
    "environment", "release", "task", "budget",
})

_IGNORED_TRANSACTIONS = re.compile(r"(^|\s)/(health|docs|openapi\.json|favicon\.ico)\b")


# ------------------------------------------------------------------ hashing
def case_hash(case_id: str) -> str:
    """Keyed hash (HMAC) so case IDs in Sentry cannot be guessed back."""
    key = os.getenv("CASE_HASH_KEY", "dev").encode()
    return hmac.new(key, str(case_id).encode(), hashlib.sha256).hexdigest()[:16]


# ------------------------------------------------------------------ scrubbing
def scrub_text(value: str) -> str:
    for pattern, replacement in _PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _strip_query(url: str) -> str:
    return url.split("?", 1)[0] if isinstance(url, str) else url


_SENSITIVE_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:" + "|".join(re.escape(k) for k in SENSITIVE_KEYS) + r")", re.IGNORECASE)


def _sensitive(key: Any) -> bool:
    """A key is sensitive when a denylisted word starts one of its parts.
    ``patient_text`` and ``attachment_url`` match; ``contexts`` and ``span_id`` do not."""
    k = str(key).lower()
    if k in SAFE_KEYS:
        return False
    return bool(_SENSITIVE_RE.search(k))


def scrub(value: Any, depth: int = 0) -> Any:
    """Recursively mask free text and drop values under sensitive keys."""
    if depth > 12:
        return FILTERED
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {k: (v if str(k) in SAFE_KEYS and isinstance(v, (str, int, float, bool))
                    else FILTERED if _sensitive(k) else scrub(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(v, depth + 1) for v in value]
    return value


def _scrub_request(request: dict) -> dict:
    out = {k: v for k, v in request.items() if k in ("method", "url", "headers")}
    if "url" in out:
        out["url"] = _strip_query(out["url"])
    if isinstance(out.get("headers"), dict):
        out["headers"] = {k: v for k, v in out["headers"].items()
                          if k.lower() in ("content-type", "user-agent", "sentry-trace", "baggage")}
    return out


def _scrub_spans(spans: list) -> list:
    for span in spans or []:
        if isinstance(span.get("description"), str):
            span["description"] = scrub_text(_strip_query(span["description"]))
        if isinstance(span.get("data"), dict):
            data = scrub(span["data"])
            for k in ("url", "http.url", "url.full"):
                if k in data:
                    data[k] = _strip_query(data[k])
            data.pop("http.query", None)
            data.pop("url.query", None)
            span["data"] = data
    return spans


def scrub_event(event: dict, _hint: Any = None) -> dict:
    """before_send / before_send_transaction: the last gate before data leaves."""
    for key in ("message", "extra", "breadcrumbs"):
        if key in event:
            event[key] = scrub(event[key])
    if isinstance(event.get("logentry"), dict):
        event["logentry"] = scrub(event["logentry"])
    for exc in (event.get("exception") or {}).get("values", []) or []:
        if isinstance(exc.get("value"), str):
            exc["value"] = scrub_text(exc["value"])
        for frame in (exc.get("stacktrace") or {}).get("frames", []) or []:
            frame.pop("vars", None)  # belt and braces on top of stack_frame_variables=False
            for key in ("pre_context", "context_line", "post_context"):
                if key in frame:
                    frame[key] = scrub(frame[key])
    if isinstance(event.get("request"), dict):
        event["request"] = _scrub_request(event["request"])
    if isinstance(event.get("tags"), dict):
        event["tags"] = {k: v if k in SAFE_KEYS else scrub(v) for k, v in event["tags"].items()}
    if isinstance(event.get("contexts"), dict):
        event["contexts"] = {
            k: (v if k in _PASSTHROUGH_CONTEXTS else scrub(v)) for k, v in event["contexts"].items()
        }
        trace = event["contexts"].get("trace")
        if isinstance(trace, dict) and isinstance(trace.get("data"), dict):
            trace["data"] = scrub(trace["data"])
    if "spans" in event:
        event["spans"] = _scrub_spans(event["spans"])
    event.pop("user", None)
    return event


def scrub_breadcrumb(crumb: dict, _hint: Any = None) -> dict | None:
    if crumb.get("category") in ("httplib", "http") and isinstance(crumb.get("data"), dict):
        crumb["data"]["url"] = _strip_query(crumb["data"].get("url", ""))
        crumb["data"].pop("http.query", None)
    return scrub(crumb)


def scrub_log(log: dict, _hint: Any = None) -> dict | None:
    if isinstance(log.get("body"), str):
        log["body"] = scrub_text(log["body"])
    if isinstance(log.get("attributes"), dict):
        log["attributes"] = scrub(log["attributes"])
    return log


def scrub_metric(metric: dict, _hint: Any = None) -> dict | None:
    attrs = metric.get("attributes") or {}
    metric["attributes"] = {k: v for k, v in attrs.items()
                            if k in SAFE_METRIC_ATTRS or k.startswith("sentry.")}
    return metric


# ------------------------------------------------------------------ sampling
def traces_sampler(ctx: dict) -> float:
    """Keep every case trace, drop health checks and docs, honor the parent's decision."""
    if ctx.get("parent_sampled") is not None:
        return 1.0 if ctx["parent_sampled"] else 0.0
    name = (ctx.get("transaction_context") or {}).get("name", "") or ""
    asgi = ctx.get("asgi_scope") or {}
    path = asgi.get("path", "") if isinstance(asgi, dict) else ""
    if _IGNORED_TRANSACTIONS.search(f" {path}") or _IGNORED_TRANSACTIONS.search(f" {name}"):
        return 0.0
    return float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))


@lru_cache(maxsize=1)
def release() -> str | None:
    for key in ("SENTRY_RELEASE", "RAILWAY_GIT_COMMIT_SHA", "KOYEB_GIT_SHA", "GIT_SHA"):
        if os.getenv(key):
            return f"billo@{os.environ[key][:12]}"
    try:
        sha = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True,
                             text=True, timeout=2, check=False).stdout.strip()
        return f"billo@{sha}" if sha else None
    except (OSError, subprocess.SubprocessError):
        return None


# ------------------------------------------------------------------ init
def sentry_options(service: str, integrations: list | None = None) -> dict[str, Any]:
    """The exact options passed to sentry_sdk.init (exposed for tests)."""
    return {
        "dsn": os.getenv("SENTRY_DSN", "").strip(),
        "environment": os.getenv("SENTRY_ENVIRONMENT", "hackathon"),
        "release": release(),
        "server_name": f"billo-{service}",
        "data_collection": SAFE_DATA_COLLECTION,
        "max_request_body_size": "never",
        "traces_sampler": traces_sampler,
        "profile_session_sample_rate": float(os.getenv("SENTRY_PROFILE_SESSION_SAMPLE_RATE", "1.0")),
        "profile_lifecycle": "trace",
        "enable_logs": True,
        "enable_metrics": True,
        "before_send": scrub_event,
        "before_send_transaction": scrub_event,
        "before_breadcrumb": scrub_breadcrumb,
        "before_send_log": scrub_log,
        "before_send_metric": scrub_metric,
        "trace_propagation_targets": _propagation_targets(),
        "integrations": integrations or [],
    }


def _propagation_targets() -> list[str]:
    """Only send trace headers to Billo's own services, never to external APIs."""
    targets = ["localhost", "127.0.0.1"]
    for key in ("CORE_URL", "BRIDGE_URL", "GATEWAY_URL", "PUBLIC_BASE_URL", "CASE_MEDIC_URL"):
        url = os.getenv(key, "").strip()
        if url:
            targets.append(re.escape(url.rstrip("/")))
    return targets


def init_sentry(service: str, integrations: list | None = None) -> bool:
    """Start Sentry for one Billo service. Returns False (and does nothing) without a DSN."""
    options = sentry_options(service, integrations)
    if not options["dsn"]:
        return False
    sentry_sdk.init(**options)
    sentry_sdk.set_tag("agent", service)
    return True


# ------------------------------------------------------------------ helpers
def tag_case(case_id: str) -> None:
    """Attach the hashed case to the current scope and span (never the raw id)."""
    if not case_id:
        return
    hashed = case_hash(case_id)
    sentry_sdk.set_tag("case", hashed)
    span = sentry_sdk.get_current_span()
    if span is not None:
        span.set_data("case", hashed)


def metric(kind: str, name: str, value: float = 1.0, unit: str | None = None, **attrs: Any) -> None:
    """Trace-connected metric with only allowlisted attributes. Never raises."""
    fn: Callable[..., None] | None = getattr(sentry_sdk.metrics, kind, None)
    if fn is None:
        return
    try:
        fn(name, value, unit=unit, attributes={k: v for k, v in attrs.items() if k in SAFE_METRIC_ATTRS})
    except Exception:  # metrics must never break a patient flow
        pass


@contextmanager
def task_span(task: str, op: str, budget_ms: int, **attrs: Any) -> Iterator[Any]:
    """Observe one controlled workflow task without recording its input or output.

    The span carries a performance budget and result while metrics provide latency,
    failure and budget-breach counters. Attribute names are allowlisted and values
    must be low-cardinality labels such as ``reader=ocr`` or ``route=benefits``.
    """
    safe = {k: v for k, v in attrs.items() if k in SAFE_METRIC_ATTRS}
    started = time.perf_counter()
    result = "ok"
    with sentry_sdk.start_span(op=op, name=task) as span:
        span.set_data("task", task)
        span.set_data("budget_ms", budget_ms)
        for key, value in safe.items():
            span.set_data(key, value)
        try:
            yield span
        except Exception:
            result = "failed"
            span.set_status("internal_error")
            metric("count", "billo.task.failed", task=task, result=result, **safe)
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            slow = duration_ms > budget_ms
            span.set_data("duration_ms", round(duration_ms, 2))
            span.set_data("budget_exceeded", slow)
            metric("distribution", "billo.task.duration", duration_ms, unit="millisecond",
                   task=task, result=result, budget="exceeded" if slow else "within", **safe)
            if slow:
                metric("count", "billo.task.slow", task=task, budget="exceeded", **safe)


def diagnostics(service: str) -> dict[str, Any]:
    """Safe deployment diagnostics for health checks; never returns a DSN or token."""
    return {
        "service": service,
        "enabled": bool(os.getenv("SENTRY_DSN", "").strip()),
        "environment": os.getenv("SENTRY_ENVIRONMENT", "hackathon"),
        "release": release(),
        "trace_sample_rate": float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        "profile_sample_rate": float(os.getenv("SENTRY_PROFILE_SESSION_SAMPLE_RATE", "1.0")),
    }


def verify_webhook(secret: str, body: bytes, signature: str) -> bool:
    """Sentry signs webhooks with HMAC-SHA256(client secret, raw body) in Sentry-Hook-Signature."""
    if not (secret and signature):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())

