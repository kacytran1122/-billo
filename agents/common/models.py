"""Typed messages between Billo agents (uAgents Models = Pydantic).

Every model carries `trace`, a small dict with the Sentry `sentry-trace` and
`baggage` values, so one case = one trace across all agents.
"""
from typing import Dict, List, Optional

from uagents import Model


class Traced(Model):
    trace: Dict[str, str] = {}


# ---------- Red-Flag Screener ----------
class ScreenRequest(Traced):
    case_id: str
    text: str


class ScreenResult(Traced):
    case_id: str
    emergency: bool
    rule_id: Optional[str] = None
    message: str = ""


# ---------- Care Finder ----------
class FindCareRequest(Traced):
    case_id: str
    text: str
    near: str = "UCLA, Los Angeles, CA"
    group_safe: bool = False  # True = answer in general words (group chat)


class Place(Model):
    name: str
    kind: str  # urgent_care | clinic | er
    npi: str
    address: str
    price_low: float
    price_typical: float
    price_source: str
    hours: str
    picture_url: str = ""
    pay_domain: str = ""


class CareOptions(Traced):
    case_id: str
    places: List[Place]
    code: str  # main billing code we priced, e.g. 73560


# ---------- After-Care Organizer ----------
class BillLine(Model):
    line_no: int
    code: str
    description: str
    units: int = 1
    charge: float
    service_date: str = ""


class AfterCareRequest(Traced):
    case_id: str
    file_url: str = ""  # receipt/final bill photo; empty + demo=True uses the synthetic document
    demo: bool = False
    hospital_npi: str = ""
    payment_status: str = "unknown"  # paid | unpaid | unknown
    reply_to: str = ""


class AfterCareResult(Traced):
    case_id: str
    lines: List[BillLine]
    total: float
    hospital_npi: str
    payment_status: str  # paid | unpaid | unknown
    provider_match: bool
    estimate_amount: Optional[float] = None
    estimate_difference: Optional[float] = None
    visit_items_matched: int = 0
    next_steps: List[str] = []
    reader: str = "unknown"  # ocr | vision | demo | demo_fallback
    unreviewed_lines: int = 0  # charges OCR saw without a CPT/HCPCS code
    needs_review: List[int] = []  # vision lines OCR could not confirm
    fallback_reason: str = ""


# ---------- Care Settlement Router ----------
class SettlementRequest(Traced):
    case_id: str
    action: str  # inspect_qr | approve_qr | reimburse
    file_url: str = ""
    demo: bool = False
    review_id: str = ""
    benefit_name: str = ""
    amount: float = 0
    benefit_approved: bool = False
    explicit_approval: bool = False
    reply_to: str = ""


class SettlementResult(Traced):
    case_id: str
    action: str
    ok: bool
    status: str = ""
    settlement_id: str = ""
    trusted: bool = False
    reasons: List[str] = []
    merchant_name: str = ""
    amount: float = 0
    handoff_url: str = ""
    mode: str = ""
    error: str = ""


# ---------- iMessage Gateway <-> Coordinator ----------
class InboundText(Model):
    """Bridge -> Gateway (REST) and Gateway -> Coordinator."""
    token: str = ""
    handle_hash: str  # hashed phone number, never the raw number
    space_id: str
    text: str
    is_group: bool = False
    case_id: str = ""
    attachment_url: str = ""
    message_id: str = ""


class OutboundText(Model):
    """Coordinator -> Gateway -> Bridge."""
    space_id: str
    text: str
    case_id: str = ""


class Ack(Model):
    ok: bool = True
    detail: str = ""


# ---------- Case Medic ----------
class Alert(Model):
    """Core API -> Case Medic (REST), built from a Sentry alert webhook."""
    token: str = ""
    check: str  # bill_reader | workflow
    case_id: str = ""
    trace_id: str = ""
    title: str = ""


class MedicAction(Traced):
    case_id: str
    action: str  # retry_reader | review_record
    patient_text: str


def dump(m: Model) -> dict:
    """Model -> plain dict (works on pydantic v1 and v2)."""
    return m.model_dump() if hasattr(m, "model_dump") else m.dict()
