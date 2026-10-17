"""Sentry setup shared by all agents: 1 case = 1 trace, no health data.

Usage:
    init_sentry("coordinator")
    with case_span(msg, op="agent.red_flag", name="screen"):
        ...
    outgoing = SomeModel(..., trace=carry())
"""
import hashlib
import hmac
import re
from contextlib import contextmanager

import sentry_sdk

from .config import env

_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_MONEY = re.compile(r"\$\s?\d[\d,]*(\.\d+)?")


def case_hash(case_id: str) -> str:
    """Keyed hash (HMAC) so case IDs in Sentry cannot be guessed back."""
    key = env("CASE_HASH_KEY", "dev").encode()
    return hmac.new(key, case_id.encode(), hashlib.sha256).hexdigest()[:16]


def _scrub(event, _hint):
    """Remove anything that looks like health or personal data before it leaves."""
    def clean(value):
        if isinstance(value, str):
            value = _PHONE.sub("[phone]", value)
            return _MONEY.sub("[amount]", value)
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value

    for key in ("message", "logentry", "extra", "request", "breadcrumbs"):
        if key in event:
            event[key] = clean(event[key])
    return event


def init_sentry(service: str) -> None:
    dsn = env("SENTRY_DSN")
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=env("SENTRY_ENVIRONMENT", "hackathon"),
        traces_sample_rate=1.0,
        data_collection={"user_info": False},
        enable_logs=True,
        before_send=_scrub,
        server_name=f"billo-{service}",
    )
    sentry_sdk.set_tag("agent", service)


def carry() -> dict:
    """Trace headers to put inside an outgoing uAgents message."""
    out = {}
    tp = sentry_sdk.get_traceparent()
    bg = sentry_sdk.get_baggage()
    if tp:
        out["sentry-trace"] = tp
    if bg:
        out["baggage"] = bg
    return out


@contextmanager
def case_span(msg, op: str, name: str, case_id: str = ""):
    """Continue the sender's trace (if any) and open a span for this agent's work."""
    headers = getattr(msg, "trace", None) or {}
    cid = case_id or getattr(msg, "case_id", "") or ""
    tx = sentry_sdk.continue_trace(headers, op=op, name=name)
    with sentry_sdk.start_transaction(tx):
        if cid:
            sentry_sdk.set_tag("case", case_hash(cid))
        yield
