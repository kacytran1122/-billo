"""Billo Core API (FastAPI): the shared tools every agent uses.

Run:  cd backend/api && uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import io
import json
import math
import os
import re
import secrets
import sys
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(REPO_ROOT / ".env")  # must run before the imports below read env

import httpx  # noqa: E402
import sentry_sdk  # noqa: E402
from fastapi import FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.responses import RedirectResponse, Response  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from sentry_sdk.integrations.fastapi import FastApiIntegration  # noqa: E402
from sentry_sdk.integrations.starlette import StarletteIntegration  # noqa: E402

from . import public_links, reader, rules, store, visa  # noqa: E402
from ocr.documents import content_type  # noqa: E402

from observability.sentry import (case_hash, diagnostics, init_sentry, metric, tag_case,
                                  task_span, verify_webhook)  # noqa: E402

# Privacy-safe Sentry (see observability/sentry.py): no bodies, no query strings, no locals,
# scrubbed events/spans/logs. 4xx responses are guards doing their job, so only 5xx are issues.
init_sentry("core", integrations=[
    StarletteIntegration(transaction_style="url", failed_request_status_codes={*range(500, 600)}),
    FastApiIntegration(transaction_style="url", failed_request_status_codes={*range(500, 600)}),
])

TOKEN = os.getenv("INTERNAL_TOKEN", "dev-token")
PUBLIC = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
PUBLIC_WEB = os.getenv("PUBLIC_WEB_URL", "http://localhost:3001").rstrip("/")
LINE = os.getenv("PHOTON_LINE_ADDRESS", "")
DEMO = os.getenv("BILLO_MODE", "demo") == "demo"
CASE_VIEW_TTL_SECONDS = int(os.getenv("CASE_VIEW_TTL_SECONDS", str(30 * 24 * 60 * 60)))
MAX_IMAGE_BYTES = int(os.getenv("OCR_MAX_IMAGE_BYTES", str(20 * 1024 * 1024)))
UPLOAD_RETENTION_SECONDS = max(60, int(os.getenv("BILLO_UPLOAD_RETENTION_SECONDS", "900")))
CASE_MEDIC_URL = os.getenv("CASE_MEDIC_URL", "http://localhost:8007").rstrip("/")
SENTRY_WEBHOOK_SECRET = os.getenv("SENTRY_WEBHOOK_SECRET", "").strip()

_link_secret = os.getenv("PUBLIC_LINK_SECRET", "").strip()
_strong_internal_link_fallback = len(TOKEN) >= 32 and TOKEN != "dev-token"
_public_host = (urlparse(PUBLIC).hostname or "").lower()
_public_is_local = _public_host in {"localhost", "127.0.0.1", "::1"}
_secured_deployment = not DEMO or not _public_is_local
if _secured_deployment and not _strong_internal_link_fallback:
    raise RuntimeError(
        "INTERNAL_TOKEN must be a non-default secret of at least 32 characters for a non-local deployment"
    )
if _secured_deployment and len(_link_secret) < 32:
    raise RuntimeError(
        "PUBLIC_LINK_SECRET must be at least 32 characters for public bearer links"
    )
if _secured_deployment and not os.getenv("PUBLIC_WEB_URL", "").strip():
    raise RuntimeError("PUBLIC_WEB_URL must be set for a non-local or live deployment")
if _secured_deployment:
    for _public_name, _public_value in (("PUBLIC_BASE_URL", PUBLIC), ("PUBLIC_WEB_URL", PUBLIC_WEB)):
        _parsed_public_url = urlparse(_public_value)
        if _parsed_public_url.scheme != "https" or not _parsed_public_url.hostname:
            raise RuntimeError(f"{_public_name} must be an absolute HTTPS URL for a non-local deployment")
if _secured_deployment and len(SENTRY_WEBHOOK_SECRET) < 32:
    raise RuntimeError(
        "SENTRY_WEBHOOK_SECRET must be at least 32 characters for a non-local deployment"
    )


_UPLOAD_NAME = re.compile(r"[0-9a-f]{32}\.(?:jpg|png|webp|heic|pdf)")


def cleanup_orphaned_uploads(now: float | None = None) -> int:
    """Delete only Billo-created upload files after the short ingestion TTL."""
    upload_root = globals().get("UPLOADS")
    if not isinstance(upload_root, Path) or not upload_root.exists():
        return 0
    cutoff = (time.time() if now is None else now) - UPLOAD_RETENTION_SECONDS
    removed = 0
    for path in upload_root.iterdir():
        try:
            if (
                not _UPLOAD_NAME.fullmatch(path.name)
                or path.is_symlink()
                or not path.is_file()
                or path.stat().st_mtime > cutoff
            ):
                continue
            path.unlink()
            removed += 1
        except OSError:
            # A concurrent extraction may already have removed the file.
            continue
    return removed


async def _upload_retention_sweeper() -> None:
    interval = min(300, max(30, UPLOAD_RETENTION_SECONDS // 2))
    while True:
        await asyncio.sleep(interval)
        cleanup_orphaned_uploads()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    cleanup_orphaned_uploads()
    sweeper = asyncio.create_task(_upload_retention_sweeper())
    try:
        yield
    finally:
        sweeper.cancel()
        with suppress(asyncio.CancelledError):
            await sweeper


app = FastAPI(title="Billo Core API", version="0.1.0", lifespan=_lifespan)


def auth(token: str | None) -> None:
    if token != TOKEN:
        raise HTTPException(401, "bad internal token")


PRIVATE_RESPONSE_HEADERS = {
    "Cache-Control": "private, no-store, max-age=0",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
}


def _private_response(response: Response) -> None:
    response.headers.update(PRIVATE_RESPONSE_HEADERS)


def _directions_url(address: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote(address)}" if address else ""


def _calendar_times(est: dict) -> tuple[float, float] | None:
    try:
        start = float(est.get("calendar_start"))
        end = float(est.get("calendar_end"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(start) or not math.isfinite(end) or start <= 0 or end <= start:
        return None
    return start, end


def _google_calendar_url(est: dict) -> str:
    times = _calendar_times(est)
    if not times:
        return ""
    start, end = times
    start_text = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(start))
    end_text = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(end))
    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote('Care plan: ' + est['place'])}&dates={start_text}/{end_text}"
        f"&details={quote('Care option saved with Billo; appointment not confirmed')}"
        f"&location={quote(est.get('address', ''))}"
    )


def _issue_case_link(case_id: str) -> dict:
    est = store.get_estimate(case_id)
    after = store.get_after_care(case_id)
    if not est and not after:
        raise HTTPException(404, "case record not found")
    token = public_links.derive(public_links.CASE_SCOPE, case_id)
    expires_at = public_links.expires_in(CASE_VIEW_TTL_SECONDS)
    store.save_public_link(
        public_links.token_hash(token), public_links.CASE_SCOPE, case_id, case_id, expires_at
    )
    result = {
        "visit_url": f"{PUBLIC_WEB}/visit/{token}",
        "token": token,
        "expires_at": public_links.iso_timestamp(expires_at),
    }
    if est and _calendar_times(est):
        result.update(
            ics_url=f"{PUBLIC}/public/cases/{token}/calendar.ics",
            gcal_url=_google_calendar_url(est),
        )
    return result


def _resolve_public_token(token: str, scope: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(404, "link not found")
    record = store.get_public_link(public_links.token_hash(token), scope)
    if not record or record["expires_at"] <= time.time():
        raise HTTPException(404, "link not found or expired")
    return record


def _iso(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


@app.middleware("http")
async def private_link_response_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/public/", "/api/link/", "/qr/", "/c/", "/letters/")):
        response.headers.update(PRIVATE_RESPONSE_HEADERS)
    return response


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
        region, location = store.resolve_location(q, near)
        out = []
        for p in store.places(region):
            stats = store.price_stats(code, region=region, include_er=p["kind"] == "er")
            if stats:
                source_name = (
                    "Synthetic demo regional price cohort"
                    if stats.get("source") == "synthetic-csv"
                    else "Regional price data"
                )
                price_low = round(float(stats["p10"]), 2)
                price_typical = round(float(stats["p50"]), 2)
                price_high = round(float(stats["p90"]), 2)
                price_source = (
                    f"{source_name} for {code} (p10/p50/p90; n={int(stats['n'])})"
                )
            else:
                price_low = round(float(p["price_low"]), 2)
                price_typical = round(float(p["price_typical"]), 2)
                price_high = round(float(p["price_high"]), 2)
                price_source = (
                    f"Curated synthetic demo estimate; no regional {code} price cohort available"
                )
            out.append({
                "name": p["name"], "kind": p["kind"], "npi": p["npi"], "address": p["address"], "hours": p["hours"],
                "price_low": price_low, "price_typical": price_typical, "price_high": price_high,
                "price_source": price_source,
                "pay_domain": p.get("pay_domain", ""),
            })
        return {"code": code, "location": location, "data_mode": "demo", "places": out}


# ------------------------------------------------------------------ Good Faith Estimate + calendar
class EstimateIn(BaseModel):
    case_id: str
    npi: str
    place: str
    code: str = ""
    amount: float
    address: str = ""
    hours: str = ""
    source_label: str = ""
    data_mode: str = ""
    region: str = ""
    kind: str = ""
    calendar_start: float | None = None
    calendar_end: float | None = None


@app.post("/estimates")
def save_estimate(body: EstimateIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    if body.amount < 0:
        raise HTTPException(422, "estimate amount must be non-negative")
    if (body.calendar_start is None) != (body.calendar_end is None):
        raise HTTPException(422, "calendar start and end must be supplied together")
    if body.calendar_start is not None and (
        not math.isfinite(body.calendar_start)
        or not math.isfinite(body.calendar_end or float("nan"))
        or body.calendar_start <= 0
        or float(body.calendar_end) <= body.calendar_start
        or float(body.calendar_end) - body.calendar_start > 24 * 60 * 60
    ):
        raise HTTPException(422, "calendar time range is invalid")
    matched_place = next((place for place in store.places() if place.get("npi") == body.npi), {})
    now = time.time()
    data_mode = body.data_mode or ("demo" if DEMO else "live")
    if data_mode not in {"demo", "live"}:
        raise HTTPException(422, "data_mode must be demo or live")
    saved = {
        **body.model_dump(exclude_none=True),
        "address": body.address or matched_place.get("address", ""),
        "hours": body.hours or matched_place.get("hours", ""),
        "region": body.region or matched_place.get("region", ""),
        "kind": body.kind or matched_place.get("kind", ""),
        "source_label": body.source_label or (
            "Synthetic demo estimate" if data_mode == "demo" else "Saved care estimate"
        ),
        "data_mode": data_mode,
        "as_of": _iso(now),
    }
    store.save_estimate(body.case_id, saved)
    links = _issue_case_link(body.case_id)
    return {"amount": body.amount, **links}


class CaseLinkIn(BaseModel):
    case_id: str


@app.post("/case-links")
def create_case_link(body: CaseLinkIn, x_internal_token: str | None = Header(None)):
    """Create or refresh the stable, opaque visit URL for one private case."""
    auth(x_internal_token)
    return _issue_case_link(body.case_id)


def _ics_escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@app.get("/public/cases/{token}/calendar.ics")
def public_case_calendar(token: str):
    link = _resolve_public_token(token, public_links.CASE_SCOPE)
    est = store.get_estimate(link["case_id"])
    times = _calendar_times(est or {})
    if not est or not times:
        raise HTTPException(404, "confirmed calendar time not found")
    start, end = times
    t0 = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(start))
    t1 = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(end))
    uid = public_links.token_hash(token)[:24]
    body = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Billo//Care Plan//EN\r\nBEGIN:VEVENT\r\n"
        f"UID:{uid}@getbillo.us\r\nDTSTART:{t0}\r\nDTEND:{t1}\r\n"
        f"SUMMARY:{_ics_escape('Care plan: ' + est['place'])}\r\n"
        "DESCRIPTION:Care option and estimate saved with Billo. Appointment not confirmed.\r\n"
        f"LOCATION:{_ics_escape(est.get('address', ''))}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    return Response(
        body,
        media_type="text/calendar",
        headers={**PRIVATE_RESPONSE_HEADERS, "Content-Disposition": "attachment; filename=billo-visit.ics"},
    )


# ------------------------------------------------------------------ live visit log
class VisitIn(BaseModel):
    case_id: str
    text: str


@app.post("/visit-events")
def visit_event(body: VisitIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    services = rules.visit_service_candidates_from_text(body.text)
    gfe = store.get_estimate(body.case_id)
    base = float(gfe["amount"]) if gfe else 0
    region = str((gfe or {}).get("region") or "")
    include_er = (gfe or {}).get("kind") == "er"
    priced: list[str] = []
    unpriced: list[str] = []
    ambiguous: list[dict] = []
    for label, candidates in services:
        if len(candidates) > 1:
            store.add_visit_event(
                body.case_id, label, "|".join(candidates), None, "ambiguous-code"
            )
            ambiguous.append({"service": label, "candidate_codes": list(candidates)})
            continue
        code = candidates[0]
        # Missing location metadata or local data must never fall back to the
        # Los Angeles/outpatient default. Keep the service, but mark it unpriced.
        stats = store.price_stats(code, region=region, include_er=include_er) if region else None
        item = _SERVICE_LABELS.get(code) or label
        if stats:
            store.add_visit_event(
                body.case_id, item, code, stats["p50"], str(stats.get("source") or "estimated")
            )
            priced.append(code)
        else:
            store.add_visit_event(body.case_id, item, code, None, "unpriced-location")
            unpriced.append(code)
    total, _n = store.visit_running_total(body.case_id)
    if not services:
        return {
            "say": "Visit log updated. I could not match that service to a billing code, so no amount was added. You can send the service name or billing code for another check.",
            "total": base + total,
        }
    if ambiguous and not priced and not unpriced:
        details = "; ".join(
            f"{item['service']} needs " + " or ".join(item["candidate_codes"])
            for item in ambiguous
        )
        return {
            "say": (
                f"Visit log updated. {details}. Send the exact billing code from the visit paperwork "
                "to add a location-appropriate estimate; no amount was added for the ambiguous service."
            ),
            "total": base + total,
            "ambiguous_services": ambiguous,
        }
    if unpriced and not priced:
        return {
            "say": (
                "Visit log updated. I recorded the service, but no location-appropriate price data "
                "is available for it, so it remains unpriced and no amount was added."
            ),
            "total": base + total,
            "unpriced_codes": unpriced,
            "ambiguous_services": ambiguous,
        }
    qualifiers: list[str] = []
    if unpriced:
        qualifiers.append(
            f"{len(unpriced)} additional service item(s) were recorded as unpriced because local data was unavailable."
        )
    if ambiguous:
        qualifiers.append(
            f"{len(ambiguous)} ambiguous service item(s) need the exact billing code before any amount is added."
        )
    qualifier = " " + " ".join(qualifiers) if qualifiers else ""
    return {
        "say": (
            f"Visit log updated. Current estimated total: ${base + total:,.0f} "
            f"(${base:,.0f} saved care estimate plus {len(priced)} matched service item(s) with local price data)."
            f"{qualifier} This is an estimate, not a final provider quote."
        ),
        "total": base + total,
        "unpriced_codes": unpriced,
        "ambiguous_services": ambiguous,
    }


# ------------------------------------------------------------------ uploads (bill photos from iMessage)
def _uploads_dir() -> Path:
    configured = os.getenv("BILLO_UPLOADS_DIR", "").strip()
    if not configured:
        return BACKEND_ROOT / "api" / "uploads"
    path = Path(configured)
    return path if path.is_absolute() else REPO_ROOT / path


UPLOADS = _uploads_dir()


@app.post("/files")
async def upload(request: Request, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    cleanup_orphaned_uploads()
    try:
        content_length = int(request.headers.get("content-length") or 0)
    except ValueError as exc:
        raise HTTPException(400, "invalid content length") from exc
    if content_length > MAX_IMAGE_BYTES:
        raise HTTPException(413, "bill image is too large")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "bill image is too large")
        data.extend(chunk)
    if not data:
        raise HTTPException(400, "bill image is empty")
    try:
        mime = content_type(bytes(data))
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    UPLOADS.mkdir(parents=True, exist_ok=True)
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
           "image/heic": "heic", "application/pdf": "pdf"}[mime]
    name = f"{secrets.token_hex(16)}.{ext}"
    descriptor = os.open(UPLOADS / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
    return {"file_url": f"file:{name}"}


# ------------------------------------------------------------------ asynchronous operation correlation
class OperationIn(BaseModel):
    case_id: str
    kind: str
    request_id: str


def _validate_operation(body: OperationIn) -> None:
    if not body.case_id.strip() or not body.request_id.strip():
        raise HTTPException(422, "case_id and request_id are required")
    if body.kind not in store.OPERATION_KINDS:
        raise HTTPException(422, "kind must be after_care or settlement")


@app.post("/operations/start")
def start_operation(body: OperationIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    _validate_operation(body)
    store.start_operation(body.case_id, body.kind, body.request_id)
    return {"ok": True}


@app.post("/operations/cancel")
def cancel_operation(body: OperationIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    _validate_operation(body)
    return {"canceled": store.cancel_operation(body.case_id, body.kind, body.request_id)}


def _without_operation_identifiers(value):
    if isinstance(value, dict):
        return {
            key: _without_operation_identifiers(item)
            for key, item in value.items()
            if key not in {"case_id", "request_id"}
        }
    if isinstance(value, list):
        return [_without_operation_identifiers(item) for item in value]
    return value


def _wallet_handoff_fields(case_id: str, result: dict) -> dict | None:
    """Reissue a deterministic bearer URL from its hash-only registry record."""
    settlement_id = str(result.get("settlement_id") or "")
    if not settlement_id:
        return None
    settlement = store.get_settlement(settlement_id)
    if (
        not settlement
        or settlement.get("case_id") != case_id
        or settlement.get("status") != "handoff_ready"
    ):
        return None
    record = store.get_public_link_by_subject(public_links.WALLET_SCOPE, settlement_id)
    if record and record.get("case_id") != case_id:
        return None
    token = public_links.derive(public_links.WALLET_SCOPE, settlement_id)
    token_hash = public_links.token_hash(token)
    if (
        not record
        or record.get("token_hash") != token_hash
        or float(record.get("expires_at") or 0) <= time.time()
    ):
        expires_at = public_links.expires_in(visa.WALLET_LINK_TTL_SECONDS)
        store.save_public_link(
            token_hash, public_links.WALLET_SCOPE, case_id, settlement_id, expires_at,
        )
    else:
        expires_at = float(record["expires_at"])
    return {
        "handoff_url": f"{PUBLIC_WEB}/wallet/{token}",
        "wallet_api_url": f"{PUBLIC}/public/wallet/{token}",
        "handoff_expires_at": public_links.iso_timestamp(expires_at),
    }


def _operation_status_response(case_id: str, operation: dict) -> dict:
    response = _without_operation_identifiers(operation)
    if response.get("status") != "completed" or response.get("action") != "approve_qr":
        return response
    result = response.get("result")
    links = _wallet_handoff_fields(case_id, result) if isinstance(result, dict) else None
    if not links:
        return {"status": "inactive"}
    result.update(links)
    return response


def _operation_mutation_response(case_id: str, action: str, result: dict) -> dict:
    response = _without_operation_identifiers(result)
    if action == "approve_qr":
        links = _wallet_handoff_fields(case_id, response)
        if not links:
            raise HTTPException(409, "wallet handoff is unavailable or expired")
        response.update(links)
    elif action == "inspect_qr":
        settlement_id = str(response.get("settlement_id") or "")
        durable = store.get_settlement(settlement_id) if settlement_id else None
        if durable:
            for key in ("currency", "invoice", "invoice_checked", "direction"):
                if key in durable:
                    response[key] = durable[key]
    return response


@app.post("/operations/status")
def operation_status(body: OperationIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    _validate_operation(body)
    return _operation_status_response(
        body.case_id,
        store.operation_status(body.case_id, body.kind, body.request_id),
    )


def _run_operation(case_id: str, kind: str, request_id: str, action: str, callback):
    try:
        result = store.run_operation(case_id, kind, request_id, action, callback)
    except store.OperationInactive as exc:
        raise HTTPException(409, str(exc)) from exc
    return _operation_mutation_response(case_id, action, result)


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
            bill = reader.read_bill(body.file_url, body.demo, body.strict)
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
    request_id: str
    lines: list[dict]
    hospital_npi: str = ""
    payment_status: str = "unknown"
    reader: str = ""
    document_type: str = ""
    needs_review: list[int] = []
    unreviewed_lines: list[int] = []
    fallback_reason: str = ""


@app.post("/after-care/organize")
def organize_after_care(body: AfterCareIn, x_internal_token: str | None = Header(None)):
    """Create a factual care record. This does not decide that any benefit is available."""
    auth(x_internal_token)
    tag_case(body.case_id)
    return _run_operation(
        body.case_id, "after_care", body.request_id, "after_care",
        lambda: _organize_after_care(body),
    )


def _organize_after_care(body: AfterCareIn):
    if body.payment_status not in {"paid", "unpaid", "unknown"}:
        raise HTTPException(422, "payment_status must be paid, unpaid, or unknown")
    # OCR charge is the printed extended line total; multiplying by quantity
    # again overstates multi-unit charges (e.g. 2 x $38.50 = $77, not $154).
    total = round(sum(float(line.get("charge", 0)) for line in body.lines), 2)
    est = store.get_estimate(body.case_id)
    estimate_amount = float(est["amount"]) if est else None
    estimate_difference = round(total - estimate_amount, 2) if estimate_amount is not None else None
    provider_match = bool(body.hospital_npi) and bool(est) and body.hospital_npi == est.get("npi")
    logged = store.visit_codes(body.case_id) or set()
    document_codes = {str(line.get("code", "")) for line in body.lines if line.get("code")}
    matched = len(logged & document_codes)
    next_steps = []
    if body.payment_status == "paid":
        next_steps.append("No payment is needed; check benefits only if you have a real coverage source.")
    elif body.payment_status == "unpaid":
        next_steps.append("Review the amount due and use the provider's official payment channel if you choose to pay.")
    else:
        next_steps.append("Confirm whether this document is paid or unpaid before any payment action.")
    next_steps.append("Track follow-up care, records, and future costs from this visit.")
    stored_lines = [
        {
            "line_no": int(line.get("line_no") or index),
            "code": str(line.get("code") or "")[:32],
            "description": str(line.get("description") or "")[:160],
            "units": int(float(line.get("units") or 1)),
            "charge": round(float(line.get("charge") or 0), 2),
            "service_date": str(line.get("service_date") or "")[:20],
        }
        for index, line in enumerate(body.lines, 1)
    ]
    valid_line_numbers = {line["line_no"] for line in stored_lines}
    needs_review = sorted({number for number in body.needs_review if number in valid_line_numbers})
    unreviewed_lines = sorted({number for number in body.unreviewed_lines if number in valid_line_numbers})
    next_steps.insert(
        0,
        "Compare the flagged lines with the original document before relying on this record."
        if needs_review or unreviewed_lines
        else "Keep this organized record with the original document.",
    )
    inferred_reader = body.reader or next(
        (str(line.get("source")) for line in body.lines if line.get("source")),
        "demo" if DEMO else "unknown",
    )
    document_type = body.document_type or (
        "receipt" if body.payment_status == "paid" else "bill" if body.payment_status == "unpaid" else "unknown"
    )
    record = {
        "case_id": body.case_id, "hospital_npi": body.hospital_npi, "total": total,
        "payment_status": body.payment_status, "provider_match": provider_match,
        "estimate_amount": estimate_amount, "estimate_difference": estimate_difference,
        "visit_items_matched": matched, "next_steps": next_steps, "lines": stored_lines,
        "reader": inferred_reader, "document_type": document_type,
        # Persist only line-number review metadata. The canonical extracted
        # values already live in `lines`, so copying raw OCR rows here would
        # increase the amount of sensitive document content we retain.
        "needs_review": needs_review, "unreviewed_lines": unreviewed_lines,
        "fallback_reason": str(body.fallback_reason or "")[:160],
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


# ------------------------------------------------------------------ private-by-link case and wallet views
_SERVICE_LABELS = {
    "73560": "Knee X-ray",
    "73562": "Knee X-ray",
    "99213": "Office visit",
    "99214": "Office visit",
    "29505": "Splint application",
    "L1830": "Knee immobilizer",
}


def _public_visit_item(event: dict) -> dict:
    stored_code = str(event.get("code") or "")
    candidates = [code for code in stored_code.split("|") if code]
    ambiguous = event.get("source_id") == "ambiguous-code" or len(candidates) > 1
    amount = (
        round(float(event["est_price"]), 2) if event.get("est_price") is not None else None
    )
    if ambiguous:
        qualifier = "Exact code needed: " + " or ".join(candidates)
        source_label = "No amount added until the exact billing code is known"
    elif amount is None:
        qualifier = "unpriced"
        source_label = "No location-appropriate price data available"
    else:
        qualifier = "estimated"
        source_label = str(event.get("source_id") or "Estimated price")
    return {
        "label": (
            str(event.get("item") or "Visit service")
            if ambiguous
            else _SERVICE_LABELS.get(stored_code) or event.get("item") or "Visit service"
        ),
        # A phrase such as "X-ray" must not be represented as one guessed code.
        "code": "" if ambiguous else stored_code,
        "amount": amount,
        "currency": "USD",
        "qualifier": qualifier,
        "source_label": source_label,
    }


def _case_data_mode(est: dict | None, after: dict | None) -> str:
    estimate_mode = str((est or {}).get("data_mode") or ("demo" if DEMO else "live")) if est else ""
    document_mode = (
        "demo" if str((after or {}).get("reader") or "").startswith("demo")
        else "patient_provided"
    ) if after else ""
    modes = {mode for mode in (estimate_mode, document_mode) if mode}
    has_demo_data = bool(modes & {"demo", "synthetic"})
    has_case_data = bool(modes & {"live", "patient_provided"})
    if has_demo_data and has_case_data:
        return "mixed"
    return estimate_mode or document_mode or ("demo" if DEMO else "live")


def _case_snapshot(case_id: str) -> dict:
    est = store.get_estimate(case_id)
    events = store.get_visit_events(case_id)
    after = store.get_after_care(case_id)
    if not est and not after:
        raise HTTPException(404, "case record not found")
    stage = "after" if after else "during" if events else "saved"
    event_items = [_public_visit_item(event) for event in events]
    updated_candidates = [float(est.get("updated_at") or 0)] if est else []
    updated_candidates.extend(float(event.get("time") or 0) for event in events)
    if after:
        updated_candidates.append(float(after.get("updated_at") or 0))
    result = {
        "stage": stage,
        "data_mode": _case_data_mode(est, after),
        "updated_at": _iso(max(updated_candidates) or time.time()),
        "provider": (
            {
                "name": est.get("place", ""),
                "address": est.get("address", ""),
                "hours": est.get("hours", ""),
                "directions_url": _directions_url(est.get("address", "")),
            }
            if est else None
        ),
        "estimate": (
            {
                "amount": round(float(est.get("amount") or 0), 2),
                "currency": "USD",
                "source_label": est.get("source_label") or "Saved care estimate",
                "as_of": est.get("as_of") or _iso(float(est.get("updated_at") or time.time())),
            }
            if est else None
        ),
        "calendar": (
            {
                # Filled by the route because the bearer token is deliberately
                # not available from a stored case record.
                "ics_url": "",
                "google_url": _google_calendar_url(est),
            }
            if est and _calendar_times(est) else None
        ),
        "visit": {
            "items": event_items,
            "running_total": round(
                float((est or {}).get("amount") or 0)
                + sum(float(item["amount"]) for item in event_items if item["amount"] is not None),
                2,
            ),
            "currency": "USD",
        },
        "document": None,
    }
    if after:
        payment_status = after.get("payment_status", "unknown")
        document_type = after.get("document_type") or (
            "receipt" if payment_status == "paid" else "bill" if payment_status == "unpaid" else "unknown"
        )
        needs_review = {
            int(number) for number in after.get("needs_review") or []
            if str(number).isdigit()
        }
        unreviewed_lines = {
            int(number) for number in after.get("unreviewed_lines") or []
            if str(number).isdigit()
        }
        lines = [
            {
                "line_no": int(line.get("line_no") or index),
                "code": str(line.get("code") or ""),
                "label": str(line.get("description") or ""),
                "description": str(line.get("description") or ""),
                "units": int(line.get("units") or 1),
                "amount": round(float(line.get("charge") or 0), 2),
                "currency": "USD",
                "service_date": str(line.get("service_date") or ""),
                "needs_review": int(line.get("line_no") or index) in needs_review | unreviewed_lines,
                "review_reasons": [
                    reason
                    for flagged, reason in (
                        (int(line.get("line_no") or index) in unreviewed_lines, "No readable billing code"),
                        (int(line.get("line_no") or index) in needs_review, "Extracted value needs confirmation"),
                    )
                    if flagged
                ],
            }
            for index, line in enumerate(after.get("lines") or [], 1)
        ]
        review_needed = bool(needs_review or unreviewed_lines)
        document_label = (
            "Receipt" if document_type == "receipt" else
            "Bill" if document_type == "bill" else
            "Bill or receipt"
        )
        result["document"] = {
            "type": document_type,
            "payment_status": payment_status,
            "total": round(float(after.get("total") or 0), 2),
            "currency": "USD",
            "estimate_difference": (
                round(float(after["estimate_difference"]), 2)
                if after.get("estimate_difference") is not None else None
            ),
            "provider_match": bool(after.get("provider_match")),
            "reader": after.get("reader") or "unknown",
            "review_status": "review_needed" if review_needed else "organized",
            "needs_review": sorted(needs_review),
            "unreviewed_lines": sorted(unreviewed_lines),
            "fallback_reason": str(after.get("fallback_reason") or ""),
            "lines": lines,
            "next_steps": list(after.get("next_steps") or []),
            "summary": f"{document_label} organized from {len(lines)} charge line(s).",
        }
    settlement = store.latest_wallet_handoff(case_id)
    if settlement and settlement.get("settlement_id"):
        wallet_record = store.get_public_link_by_subject(
            public_links.WALLET_SCOPE, settlement["settlement_id"]
        )
        if wallet_record and wallet_record["expires_at"] > time.time():
            wallet_token = public_links.derive(
                public_links.WALLET_SCOPE, settlement["settlement_id"]
            )
            if public_links.token_hash(wallet_token) == wallet_record["token_hash"]:
                result["wallet_url"] = f"{PUBLIC_WEB}/wallet/{wallet_token}"
    return result


@app.get("/public/cases/{token}")
def public_case(token: str, response: Response):
    link = _resolve_public_token(token, public_links.CASE_SCOPE)
    result = _case_snapshot(link["case_id"])
    if result["calendar"] is not None:
        result["calendar"]["ics_url"] = f"{PUBLIC}/public/cases/{token}/calendar.ics"
    _private_response(response)
    return result


@app.get("/public/wallet/{token}")
def public_wallet(token: str, response: Response):
    link = _resolve_public_token(token, public_links.WALLET_SCOPE)
    settlement = store.get_settlement(link["subject_id"])
    if (
        not settlement
        or settlement.get("case_id") != link["case_id"]
        or settlement.get("status") != "handoff_ready"
    ):
        raise HTTPException(404, "wallet handoff not found")
    trusted = bool(settlement.get("trusted"))
    checks = [
        {"id": "network", "label": "Visa payment network", "passed": trusted},
        {"id": "merchant", "label": "Merchant matches the care provider", "passed": trusted},
        {"id": "amount", "label": "Amount matches the reviewed bill", "passed": trusted},
        {"id": "currency", "label": "Currency matches", "passed": trusted},
    ]
    if settlement.get("invoice_checked"):
        checks.append({"id": "invoice", "label": "Invoice reference matches", "passed": trusted})
    _private_response(response)
    return {
        "mode": settlement.get("mode") or visa.QR_MODE,
        "status": settlement["status"],
        "merchant_name": settlement.get("merchant_name", ""),
        "amount": round(float(settlement.get("amount") or 0), 2),
        "currency": "USD" if settlement.get("currency") in {"840", "USD"} else settlement.get("currency", ""),
        "invoice": settlement.get("invoice", ""),
        "reference": (
            f"…{str(settlement.get('settlement_id', ''))[-8:]}"
            if settlement.get("settlement_id") else ""
        ),
        "checks": checks,
    }


# ------------------------------------------------------------------ guarded Visa settlement routing
class VisaQrInspectIn(BaseModel):
    case_id: str
    request_id: str
    file_url: str = ""
    qr_payload: str = ""
    demo: bool = False
    expected_invoice: str = ""


@app.post("/visa/qr/inspect")
def visa_qr_inspect(body: VisaQrInspectIn, x_internal_token: str | None = Header(None)):
    """Inspect a clinic QR against the already-reviewed unpaid bill. No money moves."""
    auth(x_internal_token)
    return _run_operation(
        body.case_id, "settlement", body.request_id, "inspect_qr",
        lambda: _visa_qr_inspect(body),
    )


def _visa_qr_inspect(body: VisaQrInspectIn):
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
            opaque_case = public_links.derive(public_links.INVOICE_SCOPE, body.case_id)[:8].upper()
            expected_invoice = expected_invoice or f"BILLO-{opaque_case}"
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
    request_id: str
    review_id: str
    explicit_approval: bool = False


@app.post("/visa/qr/approve")
def visa_qr_approve(body: VisaQrApproveIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    def approve():
        if not body.explicit_approval:
            raise HTTPException(409, "explicit patient approval is required")
        try:
            return visa.approve_qr(body.case_id, body.review_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        except NotImplementedError as exc:
            raise HTTPException(501, str(exc)) from exc
    return _run_operation(
        body.case_id, "settlement", body.request_id, "approve_qr", approve,
    )


class VisaReimburseIn(BaseModel):
    case_id: str
    request_id: str
    benefit_name: str
    amount: float
    benefit_approved: bool = False
    explicit_patient_approval: bool = False


@app.post("/visa/reimbursement/payout")
def visa_reimbursement(body: VisaReimburseIn, x_internal_token: str | None = Header(None)):
    """Create an idempotent payout only after external benefit approval and patient consent."""
    auth(x_internal_token)
    return _run_operation(
        body.case_id, "settlement", body.request_id, "reimburse",
        lambda: _visa_reimbursement(body),
    )


def _visa_reimbursement(body: VisaReimburseIn):
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


class LineIn(BaseModel):
    case_id: str
    line: dict
    all_lines: list[dict]


def _case_price_context(case_id: str) -> tuple[str, bool] | None:
    """Return the saved region and ER cohort, or no pricing context at all."""
    estimate = store.get_estimate(case_id)
    region = str((estimate or {}).get("region") or "").strip()
    kind = str((estimate or {}).get("kind") or "").strip()
    if not region or not kind:
        return None
    return region, kind == "er"


def _price_stats_for_context(code: str, context: tuple[str, bool] | None) -> dict | None:
    if not context:
        return None
    return store.price_stats(code, region=context[0], include_er=context[1])


@app.post("/audit/line")
def audit_line(body: LineIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    hits = rules.rules_check(body.line, body.all_lines, store.visit_codes(body.case_id))
    context = _case_price_context(body.case_id)
    stats = _price_stats_for_context(body.line["code"], context)
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
    gfe = est["amount"] if est else None
    context = _case_price_context(body.case_id)
    sum_p90 = sum(
        (_price_stats_for_context(line["code"], context) or {"p90": line["charge"]})["p90"]
        for line in body.lines
    )
    flags = [f for f in [rules.gfe_check(body.lines, gfe, sum_p90)] if f]
    disputed = rules.disputed_amount(body.lines, body.line_flags + flags, gfe)
    hint = (
        "Ask the provider for its financial-assistance policy, eligibility rules, application, and "
        "interest-free payment-plan options. Eligibility and deadlines vary by provider and location."
    )
    return {"flags": flags, "disputed_amount": disputed, "charity_care_hint": hint}


@app.post("/disputes/letter")
def dispute_letter(body: dict, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    # A generic letter could assert facts or legal rights that do not apply to
    # this case. Fail closed until exact disputed lines and reviewed evidence
    # are stored for an evidence-backed draft.
    case_id = str(body.get("case_id") or "")
    if not case_id or (not store.get_estimate(case_id) and not store.get_after_care(case_id)):
        raise HTTPException(404, "case record not found")
    raise HTTPException(
        409,
        "An evidence-backed dispute letter is not available yet. Review the flagged lines with the provider first.",
    )


@app.get("/letters/{token}.txt")
def letter(token: str):
    # Old issued links also fail closed rather than serving a generic claim.
    _resolve_public_token(token, public_links.LETTER_SCOPE)
    raise HTTPException(410, "This letter is unavailable; return to Billo to review the flagged lines.")


# ------------------------------------------------------------------ one-time channel join
_LINK_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class LinkCodeIn(BaseModel):
    case_id: str
    channel: str = "imessage"


def _normalize_link_code(value: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", value.upper())
    if re.fullmatch(r"BILLO[A-Z2-9]{8}", compact):
        return f"BILLO-{compact[5:9]}-{compact[9:13]}"
    return value.upper().strip()


def _handoff_deep_link(channel: str, code: str) -> str:
    if channel == "whatsapp_business":
        channels = {
            value.strip() for value in os.getenv("PHOTON_CHANNELS", "imessage").split(",") if value.strip()
        }
        if "whatsapp_business" not in channels or os.getenv("PHOTON_API_VERSION", "").strip().lower() == "beta":
            return ""
        number = re.sub(r"\D", "", os.getenv("PHOTON_WHATSAPP_ADDRESS", "").strip())
        # A web page is not a WhatsApp destination.  Fail closed so clients can
        # suppress the CTA until the production Business number is configured.
        valid_number = number if re.fullmatch(r"[1-9]\d{7,14}", number) else ""
        return f"https://wa.me/{valid_number}?text={quote(code)}" if valid_number else ""
    return f"sms:{LINE}?&body={quote(code)}" if LINE else f"{PUBLIC_WEB}/continue/{code}"


def _public_link_status(code: str, link: dict) -> dict:
    channel = link.get("channel") or "imessage"
    deep_link = _handoff_deep_link(channel, code) if link["status"] == "waiting" else ""
    return {
        "status": link["status"],
        "channel": channel,
        "code": code,
        "display_code": code,
        "expires_at": public_links.iso_timestamp(link["expires_at"]),
        "deep_link": deep_link,
        "available": bool(deep_link),
        "case_page": f"{PUBLIC_WEB}/continue/{code}",
    }


@app.post("/link-codes")
def new_link(body: LinkCodeIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    if body.channel not in {"imessage", "sms", "whatsapp_business"}:
        raise HTTPException(422, "channel must be imessage, sms, or whatsapp_business")
    expires_at = time.time() + 15 * 60
    for _ in range(8):
        suffix = "".join(secrets.choice(_LINK_ALPHABET) for _ in range(8))
        code = f"BILLO-{suffix[:4]}-{suffix[4:]}"
        if store.save_link(code, body.case_id, expires_at, body.channel):
            break
    else:  # practically unreachable, but fail closed instead of reusing a code
        raise HTTPException(503, "could not create a one-time link code")
    deep_link = _handoff_deep_link(body.channel, code)
    return {
        "code": code,
        "channel": body.channel,
        "qr_url": f"{PUBLIC}/qr/{code}.png" if deep_link else "",
        "line": (
            os.getenv("PHOTON_WHATSAPP_ADDRESS", "").strip() if body.channel == "whatsapp_business" and deep_link
            else LINE if body.channel != "whatsapp_business" else ""
        ),
        "deep_link": deep_link,
        "available": bool(deep_link),
        # Keep the older key for current coordinator clients while ensuring it
        # contains the same safe handoff target.
        "sms": deep_link,
        "expires_in": 900,
        "expires_at": public_links.iso_timestamp(expires_at),
        "case_page": f"{PUBLIC_WEB}/continue/{code}",
    }


@app.get("/qr/{code}.png")
def qr(code: str):
    import qrcode

    normalized = _normalize_link_code(code)
    link = store.get_link(normalized)
    if not link or link["status"] != "waiting":
        raise HTTPException(404, "link code not found or expired")
    deep_link = _handoff_deep_link(link.get("channel") or "imessage", normalized)
    if not deep_link:
        raise HTTPException(404, "channel handoff is not configured")
    img = qrcode.make(deep_link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png", headers=PRIVATE_RESPONSE_HEADERS)


@app.get("/api/link/{code}")
def link_status(code: str, response: Response):
    normalized = _normalize_link_code(code)
    link = store.get_link(normalized)
    _private_response(response)
    if not link:
        return {"status": "unknown"}
    return _public_link_status(normalized, link)


@app.get("/c/{code}")
def case_page(code: str):
    """Compatibility redirect for older QR printouts."""
    normalized = _normalize_link_code(code)
    if not store.get_link(normalized):
        raise HTTPException(404, "link code not found")
    return RedirectResponse(f"{PUBLIC_WEB}/continue/{normalized}", status_code=307,
                            headers=PRIVATE_RESPONSE_HEADERS)


class ClaimIn(BaseModel):
    code: str
    handle_hash: str
    space_id: str
    channel: str = ""


@app.post("/link/claim")
def claim(body: ClaimIn, x_internal_token: str | None = Header(None)):
    auth(x_internal_token)
    if not body.handle_hash.strip() or not body.space_id.strip():
        raise HTTPException(422, "handle_hash and space_id are required")
    if body.channel and body.channel not in {"imessage", "sms", "whatsapp_business"}:
        raise HTTPException(422, "channel must be imessage, sms, or whatsapp_business")
    link = store.claim_link(
        _normalize_link_code(body.code), body.handle_hash, body.space_id, body.channel
    )
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
    if not SENTRY_WEBHOOK_SECRET:
        # Never turn a missing signing configuration into an unsigned public
        # webhook. Local development can leave it unset, but the route stays off.
        raise HTTPException(503, "signed webhook is not configured")
    raw = await request.body()
    if not verify_webhook(
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
