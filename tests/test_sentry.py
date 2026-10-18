"""Sentry privacy and Case Medic routing. Run: pytest -q tests  (no keys, no network).

The end-to-end tests start a real Sentry client with an in-memory transport and
check the exact envelopes that would leave the process.
"""
import hashlib
import hmac
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "fetch.ai"))
os.environ["BILLO_MODE"] = "demo"
os.environ["DATABASE_URL"] = ""
os.environ["SENTRY_DSN"] = ""

import httpx  # noqa: E402
import pytest  # noqa: E402
import sentry_sdk  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sentry_sdk.envelope import Envelope  # noqa: E402
from sentry_sdk.integrations.fastapi import FastApiIntegration  # noqa: E402
from sentry_sdk.integrations.starlette import StarletteIntegration  # noqa: E402
from sentry_sdk.transport import Transport  # noqa: E402

from app import main  # noqa: E402
from observability import sentry as obs  # noqa: E402

PHI = ("knee", "310-555-0199", "maya@example.com", "$412", "1,240.50", "04/12/1999")


class MemoryTransport(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.envelopes: list[Envelope] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        self.envelopes.append(envelope)

    def dump(self) -> str:
        out = []
        for env in self.envelopes:
            for item in env.items:
                out.append(item.get_bytes().decode("utf-8", "replace"))
        return "\n".join(out)


@pytest.fixture
def sentry():
    transport = MemoryTransport()
    options = obs.sentry_options("core", integrations=[
        StarletteIntegration(transaction_style="url", failed_request_status_codes={*range(500, 600)}),
        FastApiIntegration(transaction_style="url", failed_request_status_codes={*range(500, 600)}),
    ])
    options.update(dsn="https://public@o1.ingest.sentry.io/1", transport=transport,
                   profile_session_sample_rate=0.0)
    sentry_sdk.init(**options)
    yield transport
    sentry_sdk.get_client().close()
    sentry_sdk.init(dsn="")


# ------------------------------------------------------------------ config
def test_sdk_collects_no_bodies_queries_prompts_or_locals():
    opts = obs.sentry_options("core")
    dc = opts["data_collection"]
    assert dc["http_bodies"] == []
    assert dc["url_query_params"] == {"mode": "off"}
    assert dc["gen_ai"] == {"inputs": False, "outputs": False}
    assert dc["stack_frame_variables"] is False
    assert dc["database_query_data"] is False
    assert dc["user_info"] is False
    assert opts["max_request_body_size"] == "never"


def test_health_checks_are_not_traced_and_parent_decision_wins():
    assert obs.traces_sampler({"asgi_scope": {"path": "/health"}}) == 0.0
    assert obs.traces_sampler({"transaction_context": {"name": "/reader/extract"}}) == 1.0
    assert obs.traces_sampler({"parent_sampled": False}) == 0.0


def test_safe_diagnostics_never_expose_dsn(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://secret@example.ingest.sentry.io/123")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "production")
    out = obs.diagnostics("core")
    assert out["enabled"] is True and out["environment"] == "production"
    assert "dsn" not in out and "secret" not in json.dumps(out)


def test_task_span_records_budget_and_failure_metrics(monkeypatch):
    spans, metrics = [], []

    class Span:
        data = {}
        status = ""

        def set_data(self, key, value):
            self.data[key] = value

        def set_status(self, value):
            self.status = value

    @contextmanager
    def fake_span(**_kwargs):
        span = Span()
        span.data = {}
        spans.append(span)
        yield span

    monkeypatch.setattr(obs.sentry_sdk, "start_span", fake_span)
    monkeypatch.setattr(obs, "metric", lambda kind, name, value=1.0, unit=None, **attrs:
                        metrics.append((kind, name, value, unit, attrs)))
    with pytest.raises(RuntimeError):
        with obs.task_span("document-reader", "document.reader", 0, route="after-care"):
            raise RuntimeError("safe failure")
    assert spans[0].status == "internal_error" and spans[0].data["budget_exceeded"] is True
    assert {item[1] for item in metrics} >= {"billo.task.failed", "billo.task.duration", "billo.task.slow"}


# ------------------------------------------------------------------ scrubber units
def test_scrubber_masks_text_and_drops_sensitive_keys():
    event = {
        "message": "call 310-555-0199 about $412.00",
        "exception": {"values": [{"value": "maya@example.com owes $1,240.50",
                                  "stacktrace": {"frames": [{"vars": {"text": "knee pain"}}]}}]},
        "request": {"url": "https://core/care/search?q=knee+pain", "data": {"text": "knee"},
                    "headers": {"cookie": "x", "content-type": "application/json"}},
        "extra": {"patient_text": "knee pain", "count": 3},
        "tags": {"case": "abcd1234", "note": "dob 04/12/1999"},
        "contexts": {"trace": {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7"}},
        "spans": [{"description": "GET https://core/care/search?q=knee", "data": {"http.query": "q=knee"}}],
        "user": {"id": "+13105550199"},
    }
    out = json.dumps(obs.scrub_event(event))
    for leaked in PHI:
        assert leaked not in out
    assert "4bf92f3577b34da6a3ce929d0e0e4736" in out  # trace ids survive
    assert "abcd1234" in out                            # hashed case tag survives
    assert "vars" not in out and "user" not in event


def test_metrics_keep_only_allowlisted_attributes():
    m = obs.scrub_metric({"name": "x", "attributes": {"reader": "ocr", "text": "knee", "sentry.release": "r"}})
    assert m["attributes"] == {"reader": "ocr", "sentry.release": "r"}


def test_logs_and_breadcrumbs_are_scrubbed():
    log = obs.scrub_log({"body": "text 310-555-0199", "attributes": {"symptoms": "knee"}})
    assert "310" not in log["body"] and log["attributes"]["symptoms"] == obs.FILTERED
    crumb = obs.scrub_breadcrumb({"category": "httplib", "data": {"url": "http://core/link/resolve?handle_hash=abc"}})
    assert crumb["data"]["url"] == "http://core/link/resolve"


# ------------------------------------------------------------------ end to end (real SDK)
def test_core_errors_and_traces_leave_without_health_data(sentry, monkeypatch):
    c = TestClient(main.app, raise_server_exceptions=False)
    H = {"x-internal-token": main.TOKEN}

    def boom(*_a, **_k):
        raise RuntimeError("OCR failed for maya@example.com 310-555-0199 total $412.00")

    monkeypatch.setattr(main.reader, "read_bill", boom)
    case_id = "case-" + str(9876 * 3)  # built at runtime so source context cannot contain it
    r = c.post("/reader/extract", json={"case_id": case_id, "file_url": "", "demo": True,
                                        "text": "knee pain 04/12/1999"}, headers=H)
    assert r.status_code == 500
    c.get("/care/search", params={"q": "knee pain", "near": "UCLA"}, headers=H)
    sentry_sdk.flush()
    sent = sentry.dump()
    assert "RuntimeError" in sent  # the error did reach Sentry...
    for leaked in PHI:              # ...without any of the patient's data
        assert leaked not in sent, leaked
    assert obs.case_hash(case_id) in sent and case_id not in sent


def test_guard_4xx_is_not_a_sentry_issue(sentry):
    c = TestClient(main.app, raise_server_exceptions=False)
    r = c.post("/after-care/organize", json={"case_id": "c", "lines": [], "payment_status": "maybe"},
               headers={"x-internal-token": main.TOKEN})
    assert r.status_code == 422
    sentry_sdk.flush()
    assert '"type":"event"' not in sentry.dump().replace(" ", "")


# ------------------------------------------------------------------ webhook -> Case Medic
def _webhook_payload():
    return {"action": "triggered", "data": {"event": {
        "title": "Something odd", "issue_id": "42",
        "tags": [["check", "bill_reader"], ["case", "abcd1234"]],
        "contexts": {"trace": {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7"}},
    }}}


def test_webhook_routes_by_check_tag_and_keeps_span():
    alert = main._sentry_alert(_webhook_payload())
    assert alert["check"] == "bill_reader"  # from the tag, not the title
    assert alert["case_id"] == "abcd1234"
    assert alert["span_id"] == "00f067aa0ba902b7" and alert["issue_id"] == "42"


@pytest.mark.parametrize(("title", "check"), [
    ("Visa settlement timed out", "settlement"),
    ("iMessage delivery failed", "delivery"),
    ("Visit followup cron missed", "followup"),
    ("Provider registry unavailable", "npi"),
])
def test_webhook_classifies_recovery_task_from_safe_title(title, check):
    payload = {"data": {"event": {"title": title}}}
    assert main._sentry_alert(payload)["check"] == check


def test_webhook_requires_valid_signature(monkeypatch):
    sent = []

    async def fake_post(self, url, json=None, **_k):
        sent.append((url, json))
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(main, "SENTRY_WEBHOOK_SECRET", "s3cret")
    c = TestClient(main.app)
    body = json.dumps(_webhook_payload()).encode()
    bad = c.post("/sentry/webhook", content=body, headers={"sentry-hook-signature": "nope"})
    assert bad.status_code == 401 and not sent
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    good = c.post("/sentry/webhook", content=body,
                  headers={"sentry-hook-signature": sig, "sentry-hook-resource": "event_alert"})
    assert good.status_code == 200 and good.json() == {"forwarded": "bill_reader"}
    assert sent[0][0].endswith("/alert") and sent[0][1]["case_id"] == "abcd1234"


# ------------------------------------------------------------------ agents helpers
def test_agent_guard_errors_are_expected_but_server_errors_are_not():
    from common.tracing import expected

    req = httpx.Request("POST", "http://core/visa/qr/approve")
    assert expected(httpx.HTTPStatusError("x", request=req, response=httpx.Response(422, request=req)))
    assert not expected(httpx.HTTPStatusError("x", request=req, response=httpx.Response(503, request=req)))
    assert not expected(RuntimeError("boom"))


def test_agent_failure_carries_case_check_and_parent_trace(sentry):
    """One case = one trace: an After-Care failure joins the sender's trace with the
    tags Case Medic routes on, and no raw case id."""
    from types import SimpleNamespace

    from common.tracing import carry, case_span, check

    with sentry_sdk.start_transaction(op="billo.case", name="asi1 message") as parent:
        headers = carry()
    msg = SimpleNamespace(trace=headers, case_id="case-" + str(4321 * 2))
    with pytest.raises(RuntimeError):
        with case_span(msg, op="agent.after_care", name="organize receipt"):
            with check("bill_reader", alert_on_4xx=True):
                raise RuntimeError("reader returned bad json")
    sentry_sdk.flush()
    events = [json.loads(item.get_bytes()) for env in sentry.envelopes for item in env.items
              if item.type == "event"]
    assert len(events) == 1  # captured once even though two layers saw it
    ev = events[0]
    assert ev["tags"]["check"] == "bill_reader"
    assert ev["tags"]["case"] == obs.case_hash(msg.case_id)
    assert ev["contexts"]["trace"]["trace_id"] == parent.trace_id

