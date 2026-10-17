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


# ---------- Bill Auditor ----------
class BillLine(Model):
    line_no: int
    code: str
    description: str
    units: int = 1
    charge: float
    service_date: str = ""


class Flag(Model):
    rule_id: str  # DUP-001, NCCI-PTP, GFE-400, NOT-IN-LOG, PRICE-P90
    kind: str  # dispute | ask_hospital
    rules_check: bool
    price_check: bool
    line_nos: List[int]
    amount_at_stake: float
    explanation: str
    source_ids: List[str] = []


class AuditRequest(Traced):
    case_id: str
    file_url: str = ""  # bill photo URL; empty + demo=True uses the synthetic bill
    demo: bool = False
    hospital_npi: str = ""
    reply_to: str = ""  # who receives the streamed updates (the Coordinator)


class AuditUpdate(Traced):
    """Streamed live: one per bill line that was checked."""
    case_id: str
    line_no: int
    total_lines: int
    status: str  # ok | checking | dispute | ask_hospital
    flag: Optional[Flag] = None
    running_total: float  # possible savings so far
    text: str  # ready-to-send sentence for the patient


class AuditResult(Traced):
    case_id: str
    lines: List[BillLine]
    flags: List[Flag]
    total_billed: float
    fair_amount: float
    disputed_amount: float
    hospital_npi: str
    charity_care_hint: str = ""


# ---------- Payment Guard ----------
class PayRequest(Traced):
    case_id: str
    hospital_npi: str
    amount: float  # the fair part only
    disputed_amount: float
    mandate_max: float
    pay_link: str = ""  # link from the hospital, if any; checked by the Guard


class PayDecision(Traced):
    case_id: str
    approved: bool
    reasons: List[str]
    pay_link: str = ""
    payment_id: str = ""


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
    check: str  # npi | bill_reader | visa
    case_id: str = ""
    trace_id: str = ""
    title: str = ""


class MedicAction(Traced):
    case_id: str
    action: str  # retry_reader | npi_unverified | pause_guard
    patient_text: str


def dump(m: Model) -> dict:
    """Model -> plain dict (works on pydantic v1 and v2)."""
    return m.model_dump() if hasattr(m, "model_dump") else m.dict()
