"""Billo Core API (FastAPI): the shared tools every agent uses.

Run:  cd core && uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import io
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")  # must run before the imports below read env

import httpx  # noqa: E402
import sentry_sdk  # noqa: E402
from fastapi import FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.responses import HTMLResponse, PlainTextResponse, Response  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from sentry_sdk.integrations.fastapi import FastApiIntegration  # noqa: E402
from sentry_sdk.integrations.starlette import StarletteIntegration  # noqa: E402

from . import reader, rules, store, visa  # noqa: E402

from observability.sentry import (case_hash, diagnostics, init_sentry, metric, tag_case,
                                  task_span, verify_webhook)  # noqa: E402

# Privacy-safe Sentry (see observability/sentry.py): no bodies, no query strings, no locals,
# scrubbed events/spans/logs. 4xx responses are guards doing their job, so only 5xx are issues.
init_sentry("core", integrations=[
    StarletteIntegration(transaction_style="url", failed_request_status_codes={*range(500, 600)}),
    FastApiIntegration(transaction_style="url", failed_request_status_codes={*range(500, 600)}),
])

app = FastAPI(title="Billo Core API", version="0.1.0")
TOKEN = os.getenv("INTERNAL_TOKEN", "dev-token")
PUBLIC = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
LINE = os.getenv("PHOTON_LINE_ADDRESS", "")
DEMO = os.getenv("BILLO_MODE", "demo") == "demo"
MAX_IMAGE_BYTES = int(os.getenv("OCR_MAX_IMAGE_BYTES", str(20 * 1024 * 1024)))
CASE_MEDIC_URL = os.getenv("CASE_MEDIC_URL", "http://localhost:8007").rstrip("/")
SENTRY_WEBHOOK_SECRET = os.getenv("SENTRY_WEBHOOK_SECRET", "").strip()

if not DEMO and TOKEN == "dev-token":
    raise RuntimeError("INTERNAL_TOKEN must be set to a strong secret when BILLO_MODE=live")
if not DEMO and os.getenv("SENTRY_DSN") and not SENTRY_WEBHOOK_SECRET:
    raise RuntimeError("SENTRY_WEBHOOK_SECRET must be set when BILLO_MODE=live so /sentry/webhook is signed")


def auth(token: str | None) -> None:
    if token != TOKEN:
        raise HTTPException(401, "bad internal token")


@app.get("/health")
def health():
    return {"ok": True, "db": store.use_db(), "mode": os.getenv("BILLO_MODE", "demo"),
            "visa_qr": visa.QR_MODE, "visa_direct": visa.DIRECT_MODE,
            "observability": diagnostics("core")}


# ------------------------------------------------------------------ Care Finder
@app.get("/care/search")
def care_search(q: str = "", near: str = "UCLA", x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    with task_span("care-search", "workflow.care_search", 1000, route="care"):
        code = "73560" if any(w in q.lower() for w in ("knee", "ankle", "leg", "fall", "soccer")) else "99213"
        key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        out = []
        for p in store.places():
            pic = ""
            if key:  # Google Static Maps (satellite). Show attribution in the UI; do not cache images.
                pic = (f"https://maps.googleapis.com/maps/api/staticmap?center={p['lat']},{p['lng']}"
                       f"&zoom=18&size=600x300&maptype=satellite&markers={p['lat']},{p['lng']}&key={key}")
            stats = store.price_stats(code, include_er=p["kind"] == "er")
            out.append({
                "name": p["name"], "kind": p["kind"], "npi": p["npi"], "address": p["address"], "hours": p["hours"],
                "price_low": p["price_low"], "price_typical": p["price_typical"],
                "price_source": f"{stats['source']} p50 ${stats['p50']:,.0f} for {code}" if stats else "posted price",
                "picture_url": pic, "pay_domain": p.get("pay_domain", ""),
            })
        return {"code": code, "places": out}


# ------------------------------------------------------------------ Good Faith Estimate + calendar
class EstimateIn(BaseModel):
    case_id: str
    npi: str
    place: str
    code: str = ""
    amount: float


@app.post("/estimates")
def save_estimate(body: EstimateIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    store.save_estimate(body.case_id, body.model_dump())
    start = time.strftime("%Y%m%dT%H%M%S", time.localtime(time.time() + 3600))
    end = time.strftime("%Y%m%dT%H%M%S", time.localtime(time.time() + 7200))
    gcal = ("https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={quote('Visit: ' + body.place)}&dates={start}/{end}&details={quote('Booked with Billo')}")
    return {"amount": body.amount, "ics_url": f"{PUBLIC}/ics/{body.case_id}", "gcal_url": gcal}


@app.get("/ics/{case_id}")
def ics(case_id: str):
    est = store.get_estimate(case_id)
    if not est:
        raise HTTPException(404)
    t0 = time.strftime("%Y%m%dT%H%M%S", time.localtime(time.time() + 3600))
    t1 = time.strftime("%Y%m%dT%H%M%S", time.localtime(time.time() + 7200))
    body = ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Billo//EN\r\nBEGIN:VEVENT\r\n"
            f"UID:{case_id}@heybillo.tech\r\nDTSTART:{t0}\r\nDTEND:{t1}\r\nSUMMARY:Visit: {est['place']}\r\n"
            "DESCRIPTION:Booked with Billo. Your Good Faith Estimate is saved.\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    return Response(body, media_type="text/calendar", headers={"Content-Disposition": "attachment; filename=billo-visit.ics"})


# ------------------------------------------------------------------ live visit log
class VisitIn(BaseModel):
    case_id: str
    text: str


@app.post("/visit-events")
def visit_event(body: VisitIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    codes = rules.visit_codes_from_text(body.text)
    added = []
    for code in sorted(codes):
        stats = store.price_stats(code)
        if stats:
            store.add_visit_event(body.case_id, body.text[:60], code, stats["p50"])
            added.append(code)
    total, n = store.visit_running_total(body.case_id)
    gfe = store.get_estimate(body.case_id)
    base = gfe["amount"] if gfe else 0
    if not added:
        return {"say": "Got it. I did not find a price for that yet, but I saved it in your visit log.", "total": total}
    return {"say": f"Saved. Your visit so far: about ${base + total:,.0f} (estimate ${base:,.0f} + {n} item(s)).", "total": base + total}


# ------------------------------------------------------------------ uploads (bill photos from iMessage)
def _uploads_dir() -> Path:
    configured = os.getenv("BILLO_UPLOADS_DIR", "").strip()
    if not configured:
        return Path(__file__).resolve().parents[1] / "uploads"
    path = Path(configured)
    return path if path.is_absolute() else Path(__file__).resolve().parents[2] / path


UPLOADS = _uploads_dir()


@app.post("/files")
async def upload(request: Request, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    content_length = int(request.headers.get("content-length") or 0)
    if content_length > MAX_IMAGE_BYTES:
        raise HTTPException(413, "bill image is too large")
    data = await request.body()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "bill image is too large")
    if not data:
        raise HTTPException(400, "bill image is empty")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/heic": "heic", "application/pdf": "pdf"}.get(
        request.headers.get("content-type", ""), "bin")
    name = f"{random.getrandbits(64):016x}.{ext}"
    (UPLOADS / name).write_bytes(data)
    return {"file_url": f"file:{name}"}


# ------------------------------------------------------------------ document reader + after-care organizer
class ExtractIn(BaseModel):
    case_id: str
    file_url: str = ""
    demo: bool = False
    strict: bool = False


@app.post("/reader/extract")
def extract(body: ExtractIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    uploaded = UPLOADS / Path(body.file_url[5:]).name if body.file_url.startswith("file:") else None
    tag_case(body.case_id)
    started = time.perf_counter()
    try:
        with task_span("document-reader", "document.reader", 10000, route="after-care") as span:
            bill = reader.read_bill(body.file_url, body.demo or (DEMO and not body.file_url), body.strict)
            path = bill.get("reader", "unknown")
            span.set_data("reader", path)
            span.set_data("lines", len(bill.get("lines", [])))  # a count, never the lines
            span.set_data("needs_review", len(bill.get("needs_review", [])))
        metric("distribution", "billo.reader.duration", (time.perf_counter() - started) * 1000,
               unit="millisecond", reader=path)
        metric("count", "billo.reader.path", reader=path, agent="core")
        return bill
    except (FileNotFoundError, ValueError) as exc:
        metric("count", "billo.reader.unreadable", reader="none", agent="core")
        sentry_sdk.set_tag("check", "bill_reader")
        raise HTTPException(422, str(exc)) from exc
    finally:
        # Uploaded bills can contain health information. Remove them as soon as
        # OCR/vision has finished; extracted typed lines continue through the flow.
        if uploaded:
            uploaded.unlink(missing_ok=True)


class AfterCareIn(BaseModel):
    case_id: str
    lines: list[dict]
    hospital_npi: str = ""
    payment_status: str = "unknown"


@app.post("/after-care/organize")
def organize_after_care(body: AfterCareIn, x_internal_token: str | None = Header(None)):
    """Create a factual care record. This does not decide that any benefit is available."""
    auth(x_internal_token)
    tag_case(body.case_id)
    if body.payment_status not in {"paid", "unpaid", "unknown"}:
        raise HTTPException(422, "payment_status must be paid, unpaid, or unknown")
    total = round(sum(float(line.get("charge", 0)) * int(line.get("units", 1)) for line in body.lines), 2)
    est = store.get_estimate(body.case_id)
    estimate_amount = float(est["amount"]) if est else None
    estimate_difference = round(total - estimate_amount, 2) if estimate_amount is not None else None
    provider_match = bool(body.hospital_npi) and (not est or body.hospital_npi == est.get("npi"))
    logged = store.visit_codes(body.case_id) or set()
    document_codes = {str(line.get("code", "")) for line in body.lines if line.get("code")}
    matched = len(logged & document_codes)
    next_steps = ["Keep this verified record with the original document."]
    if body.payment_status == "paid":
        next_steps.append("No payment is needed; check benefits only if you have a real coverage source.")
    elif body.payment_status == "unpaid":
        next_steps.append("Review the amount due and use the provider's official payment channel if you choose to pay.")
    else:
        next_steps.append("Confirm whether this document is paid or unpaid before any payment action.")
    next_steps.append("Track follow-up care, records, and future costs from this visit.")
    record = {
        "case_id": body.case_id, "hospital_npi": body.hospital_npi, "total": total,
        "payment_status": body.payment_status, "provider_match": provider_match,
        "estimate_amount": estimate_amount, "estimate_difference": estimate_difference,
        "visit_items_matched": matched, "next_steps": next_steps,
    }
    store.save_after_care(body.case_id, record)
    return record


class BenefitsIn(BaseModel):
    case_id: str
    text: str = ""


@app.post("/benefits/check")
def check_benefits(body: BenefitsIn, x_internal_token: str | None = Header(None)):
    """Surface possible paths from coverage the patient names; never promise eligibility."""
    auth(x_internal_token)
    low = body.text.lower()
    catalog = [
        (("hsa", "health savings"), "HSA self-reimbursement", "receipt and proof of payment"),
        (("fsa", "flexible spending"), "FSA reimbursement", "itemized receipt and plan claim form"),
        (("hra", "health reimbursement"), "HRA reimbursement", "itemized receipt and employer plan rules"),
        (("out of network", "out-of-network", "ppo"), "Out-of-network insurance claim", "superbill and insurer claim form"),
        (("employer", "work benefit"), "Employer health benefit", "receipt and employer program terms"),
        (("university", "student benefit", "school"), "Student health benefit", "receipt and school program terms"),
        (("travel insurance",), "Travel insurance claim", "receipt, trip details, and policy terms"),
        (("accident insurance",), "Accident insurance claim", "receipt, incident details, and policy terms"),
    ]
    paths = [
        {"name": name, "status": "possible_not_confirmed", "needed": needed,
         "next_step": "Check the plan rules and submission deadline before filing."}
        for terms, name, needed in catalog
        if any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", low) for term in terms)
    ]
    result = {
        "paths": paths,
        "message": (
            "I found possible benefit paths, but eligibility depends on your plan rules."
            if paths else
            "I did not identify a coverage source. Tell me only if you have an HSA, FSA, HRA, out-of-network plan, employer, school, travel, or accident benefit."
        ),
    }
    store.save_benefit_check(body.case_id, result)
    return result


# ------------------------------------------------------------------ guarded Visa settlement routing
class VisaQrInspectIn(BaseModel):
    case_id: str
    file_url: str = ""
    qr_payload: str = ""
    demo: bool = False
    expected_invoice: str = ""


@app.post("/visa/qr/inspect")
def visa_qr_inspect(body: VisaQrInspectIn, x_internal_token: str | None = Header(None)):
    """Inspect a clinic QR against the already-reviewed unpaid bill. No money moves."""
    auth(x_internal_token)
    record = store.get_after_care(body.case_id)
    if not record or record.get("payment_status") != "unpaid":
        raise HTTPException(409, "an organized unpaid bill is required before scanning a clinic payment QR")
    est = store.get_estimate(body.case_id) or {}
    provider = est.get("place", "")
    if not provider or not record.get("provider_match"):
        raise HTTPException(409, "the clinic must match the saved care provider before QR approval")
    uploaded = UPLOADS / Path(body.file_url[5:]).name if body.file_url.startswith("file:") else None
    try:
        expected_invoice = body.expected_invoice
        if body.demo and DEMO:
            expected_invoice = expected_invoice or f"BILLO-{body.case_id}"
            payload = visa.demo_qr(provider, record["total"], expected_invoice)
        elif body.qr_payload:
            payload = body.qr_payload
        elif uploaded and uploaded.exists():
            payload = visa.decode_qr_image(uploaded.read_bytes())
        else:
            raise HTTPException(422, "send a QR image or payload")
        inspected = visa.inspect_qr(payload, provider, record["total"], expected_invoice=expected_invoice)
        return visa.save_review(body.case_id, inspected, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        if uploaded:
            uploaded.unlink(missing_ok=True)


class VisaQrApproveIn(BaseModel):
    case_id: str
    review_id: str
    explicit_approval: bool = False


@app.post("/visa/qr/approve")
def visa_qr_approve(body: VisaQrApproveIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    if not body.explicit_approval:
        raise HTTPException(409, "explicit patient approval is required")
    try:
        return visa.approve_qr(body.case_id, body.review_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc)) from exc


class VisaReimburseIn(BaseModel):
    case_id: str
    benefit_name: str
    amount: float
    benefit_approved: bool = False
    explicit_patient_approval: bool = False


@app.post("/visa/reimbursement/payout")
def visa_reimbursement(body: VisaReimburseIn, x_internal_token: str | None = Header(None)):
    """Create an idempotent payout only after external benefit approval and patient consent."""
    auth(x_internal_token)
    record = store.get_after_care(body.case_id)
    if not record or record.get("payment_status") != "paid":
        raise HTTPException(409, "a paid receipt is required before reimbursement")
    checked = store.get_benefit_check(body.case_id) or {"paths": []}
    named = {path["name"] for path in checked["paths"]}
    if body.benefit_name not in named:
        raise HTTPException(409, "the reimbursement benefit must match a checked coverage source")
    if not body.explicit_patient_approval:
        raise HTTPException(409, "explicit patient approval is required")
    if body.amount > float(record["total"]):
        raise HTTPException(409, "reimbursement cannot exceed the paid receipt total")
    try:
        return visa.reimburse(body.case_id, body.benefit_name, body.amount, body.benefit_approved)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc)) from exc


@app.get("/visa/settlements/{settlement_id}")
def visa_settlement(settlement_id: str, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    result = store.get_settlement(settlement_id)
    if not result:
        raise HTTPException(404, "settlement not found")
    return result


@app.get("/visa/qr/{review_id}", response_class=HTMLResponse)
def visa_qr_handoff(review_id: str):
    result = store.get_settlement(review_id)
    if not result or result.get("status") != "handoff_ready":
        raise HTTPException(404, "payment handoff not found")
    return ("<html><body style='font-family:sans-serif;max-width:520px;margin:60px auto'>"
            "<h2>Visa wallet handoff — simulation</h2>"
            f"<p>Verified merchant: <b>{visa.safe_text(result.get('merchant_name', ''))}</b></p>"
            f"<p>Amount: <b>${result.get('amount',0):,.2f}</b></p>"
            "<p>No card data was collected and no money moved. Connect an approved Visa Pay wallet "
            "before production.</p></body></html>")


class LineIn(BaseModel):
    case_id: str
    line: dict
    all_lines: list[dict]


@app.post("/audit/line")
def audit_line(body: LineIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    hits = rules.rules_check(body.line, body.all_lines, store.visit_codes(body.case_id))
    stats = store.price_stats(body.line["code"])
    price = rules.price_check(body.line, body.all_lines, stats)
    flag = rules.vote(body.line, hits, price)
    return {"flag": flag, "say": rules.say_for(body.line, flag), "stats": stats}


class TotalIn(BaseModel):
    case_id: str
    lines: list[dict]
    line_flags: list[dict] = []


@app.post("/audit/total")
def audit_total(body: TotalIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    est = store.get_estimate(body.case_id)
    gfe = est["amount"] if est else (240.0 if DEMO else None)  # demo: Maya's saved estimate
    sum_p90 = sum((store.price_stats(l["code"]) or {"p90": l["charge"]})["p90"] for l in body.lines)
    flags = [f for f in [rules.gfe_check(body.lines, gfe, sum_p90)] if f]
    disputed = rules.disputed_amount(body.lines, body.line_flags + flags, gfe)
    hint = ("You may also qualify for free or cheaper care (charity care): in California, hospitals must help "
            "patients up to 400% of the federal poverty level. Tell me your yearly income to check.")
    return {"flags": flags, "disputed_amount": disputed, "charity_care_hint": hint}


@app.post("/disputes/letter")
def dispute_letter(body: dict, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    # TODO(drafter): build the letter from the agreed flags only, with evidence, and store it.
    return {"url": f"{PUBLIC}/letters/{body['case_id']}.txt"}


@app.get("/letters/{case_id}.txt", response_class=PlainTextResponse)
def letter(case_id: str):
    return ("To the billing office,\n\nI am disputing charges on my bill. Details are attached: each disputed "
            "item, the rule it breaks, and the public price data. Please send an itemized bill and correct the "
            "charges. Under the No Surprises Act I am starting the dispute process for the amount over my Good "
            "Faith Estimate.\n\nThank you.\n(Drafted by Billo. Not legal advice.)\n")


# ------------------------------------------------------------------ QR join (News Next Door method)
@app.post("/link-codes")
def new_link(body: dict, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    code = f"BILLO-{random.randint(1000, 9999)}"
    store.save_link(code, body["case_id"], time.time() + 15 * 60)
    return {"code": code, "qr_url": f"{PUBLIC}/qr/{code}.png", "line": LINE, "sms": f"sms:{LINE}&body={code}",
            "expires_in": 900, "case_page": f"{PUBLIC}/c/{code}"}


@app.get("/qr/{code}.png")
def qr(code: str):
    import qrcode

    img = qrcode.make(f"sms:{LINE}&body={code}" if LINE else f"{PUBLIC}/c/{code}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.get("/api/link/{code}")
def link_status(code: str):
    link = store.get_link(code)
    if not link:
        return {"status": "unknown"}
    if link["status"] == "waiting" and time.time() > link["expires_at"]:
        link["status"] = "expired"
    return {"status": link["status"]}


@app.get("/c/{code}", response_class=HTMLResponse)
def case_page(code: str):
    """Optional page for discharge sheets. Not part of the ASI:One primary flow."""
    return (f"<html><body style='font-family:sans-serif;text-align:center;margin-top:40px'>"
            f"<h2>Text this to check your bill</h2><img src='/qr/{code}.png' width='220'/>"
            f"<p><a href='sms:{LINE}&body={code}'>Open in iMessage</a> · code <b>{code}</b></p>"
            f"<p id='s'>waiting...</p><script>setInterval(async()=>{{const r=await fetch('/api/link/{code}');"
            f"const j=await r.json();document.getElementById('s').textContent=j.status==='linked'?'Linked':j.status}},3000)"
            f"</script></body></html>")


class ClaimIn(BaseModel):
    code: str
    handle_hash: str
    space_id: str


@app.post("/link/claim")
def claim(body: ClaimIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    link = store.claim_link(body.code.upper(), body.handle_hash, body.space_id)
    if not link:
        return {"status": "unknown"}
    return {"status": link["status"], "case_id": link["case_id"] if link["status"] == "linked" else ""}


@app.get("/link/resolve")
def resolve(handle_hash: str, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    return {"case_id": store.case_for_handle(handle_hash) or ""}


@app.post("/link/stop")
def stop(body: dict, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    store.stop(body["handle_hash"])
    return {"ok": True}


@app.get("/reminders/allowed")
def allowed(case_id: str, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    return {"ok": store.reminders_allowed(case_id)}


# ------------------------------------------------------------------ Sentry -> Case Medic
def _sentry_alert(payload: dict) -> dict:
    """Turn a Sentry webhook (event alert, issue or error resource) into a small Case Medic alert.
    The check comes from the event's `check` tag; the title is only a fallback."""
    data = payload.get("data", {}) or {}
    event = data.get("event") or data.get("error") or {}
    issue = data.get("issue") or {}
    raw_tags = event.get("tags") or issue.get("tags") or []
    tags: dict[str, str] = {}
    for t in raw_tags:
        if isinstance(t, (list, tuple)) and len(t) == 2:
            tags[str(t[0])] = str(t[1])
        elif isinstance(t, dict) and "key" in t:
            tags[str(t["key"])] = str(t.get("value", ""))
    title = (event.get("title") or issue.get("title") or payload.get("message") or "").lower()
    check = tags.get("check") or (
        "bill_reader" if any(w in title for w in ("reader", "json", "ocr")) else
        "npi" if any(w in title for w in ("npi", "provider")) else
        "settlement" if any(w in title for w in ("visa", "payment", "settlement", "payout")) else
        "delivery" if any(w in title for w in ("bridge", "message", "delivery", "imessage")) else
        "followup" if any(w in title for w in ("followup", "reminder", "cron")) else "workflow")
    trace = (event.get("contexts", {}) or {}).get("trace", {}) or {}
    return {"token": TOKEN, "check": check, "case_id": tags.get("case", ""),
            "trace_id": trace.get("trace_id", ""), "span_id": trace.get("span_id", ""),
            "issue_id": str(event.get("issue_id") or issue.get("id") or ""), "title": title[:120]}


@app.post("/sentry/webhook")
async def sentry_webhook(request: Request):
    """Sentry alert webhook (Internal Integration with alert-rule action, or a webhook rule).
    Verifies Sentry-Hook-Signature, then forwards a SMALL alert to Case Medic:
    which check failed + hashed case tag + trace/span ids."""
    raw = await request.body()
    if SENTRY_WEBHOOK_SECRET and not verify_webhook(
            SENTRY_WEBHOOK_SECRET, raw, request.headers.get("sentry-hook-signature", "")):
        raise HTTPException(401, "bad sentry signature")
    resource = request.headers.get("sentry-hook-resource", "event_alert")
    if resource == "installation":
        return {"forwarded": None}
    try:
        payload = json.loads(raw or b"{}")
    except ValueError as exc:
        raise HTTPException(400, "invalid json") from exc
    alert = _sentry_alert(payload)
    if payload.get("action") == "resolved":
        return {"forwarded": None}
    with sentry_sdk.start_span(op="case_medic.forward", name=alert["check"]):
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(f"{CASE_MEDIC_URL}/alert", json=alert)
        except httpx.HTTPError as exc:
            sentry_sdk.capture_exception(exc)
            raise HTTPException(502, "case medic unreachable") from exc
    metric("count", "billo.sentry.webhook", check=alert["check"])
    return {"forwarded": alert["check"]}


@app.post("/demo/break-npi")
async def break_npi(body: dict, x_internal_token: str | None = Header(None)):
    """Demo button: raise a tagged NPI error so Sentry fires the alert -> Case Medic heals the case.
    If Sentry is slow, this also calls Case Medic directly (the backup path for the stage)."""
    auth(x_internal_token)
    case_id = body.get("case_id", "")
    hashed = case_hash(case_id) if case_id else ""
    with sentry_sdk.new_scope() as scope:
        scope.set_tag("check", "npi")
        if hashed:
            scope.set_tag("case", hashed)
        scope.fingerprint = ["billo", "npi-lookup", "demo"]
        event_id = sentry_sdk.capture_message("NPI lookup failed (demo)", level="error")
    span = sentry_sdk.get_current_span()
    alert = {"token": TOKEN, "check": "npi", "case_id": hashed, "title": "npi demo",
             "trace_id": getattr(span, "trace_id", "") or "", "span_id": getattr(span, "span_id", "") or ""}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"{CASE_MEDIC_URL}/alert", json=alert)
    except httpx.HTTPError:
        pass  # the Sentry alert -> webhook path still runs
    return {"ok": True, "event_id": event_id}
