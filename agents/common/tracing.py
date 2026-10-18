"""Sentry helpers for every agent: 1 case = 1 trace, no health data.

The privacy policy itself (what is collected, what is scrubbed) lives in
``observability/sentry.py`` and is shared with the Core API.

Usage:
    init_sentry("coordinator")
    with case_span(msg, op="agent.red_flag", name="screen"):
        with check("bill_reader"):          # failures here route Case Medic to retry_reader
            ...
        metric("count", "billo.reader.path", reader="ocr")
    outgoing = SomeModel(..., trace=carry())
"""
import sys
from contextlib import contextmanager
from typing import Iterator

import httpx
import sentry_sdk

from .config import ROOT

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from observability.sentry import case_hash, metric, tag_case  # noqa: E402
from observability.sentry import init_sentry as _init  # noqa: E402

__all__ = ["carry", "case_hash", "case_scope", "case_span", "check", "init_sentry", "metric", "tag_case"]


def init_sentry(service: str) -> bool:
    return _init(service)


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
def case_scope(case_id: str = "", channel: str = "") -> Iterator[None]:
    """Isolate tags per message. Agents handle messages concurrently, so tags set on the
    shared scope would leak from one patient's case onto another's events."""
    with sentry_sdk.isolation_scope():
        if channel:
            sentry_sdk.set_tag("channel", channel)
        tag_case(case_id)
        yield


@contextmanager
def case_span(msg, op: str, name: str, case_id: str = "") -> Iterator[None]:
    """Continue the sender's trace (if any) and open a span for this agent's work.
    Unhandled errors are captured with the case tag and ``check`` tag, then re-raised."""
    headers = getattr(msg, "trace", None) or {}
    cid = case_id or getattr(msg, "case_id", "") or ""
    with sentry_sdk.isolation_scope():
        tx = sentry_sdk.continue_trace(headers, op=op, name=name)
        with sentry_sdk.start_transaction(tx):
            tag_case(cid)
            try:
                yield
            except Exception as exc:
                if expected(exc):
                    tx.set_status("failed_precondition")
                else:
                    sentry_sdk.capture_exception(exc)
                raise


def expected(exc: BaseException) -> bool:
    """A 4xx from the Core API is a guard doing its job (QR mismatch, missing approval),
    not a bug. Those mark the span but do not raise a Sentry issue or wake Case Medic."""
    return isinstance(exc, httpx.HTTPStatusError) and 400 <= exc.response.status_code < 500


@contextmanager
def check(name: str, alert_on_4xx: bool = False) -> Iterator[None]:
    """Name the workflow check that is running. Case Medic picks its fix from this tag
    (bill_reader -> retry_reader, anything else -> review_record). Set ``alert_on_4xx``
    when a 4xx is a failure worth healing, e.g. an unreadable bill photo (422)."""
    with sentry_sdk.new_scope():
        sentry_sdk.set_tag("check", name)
        try:
            yield
        except Exception as exc:
            if alert_on_4xx or not expected(exc):
                sentry_sdk.capture_exception(exc)
                metric("count", "billo.check.failed", check=name)
            raise
