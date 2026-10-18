"""Billo Coordinator: the ONE front door on ASI:One and Photon messaging.

Fetch.ai rule: the complete primary workflow must run inside one ASI:One
conversation, with no custom frontend. This file is that workflow:

  symptoms -> Red-Flag Screener -> Care Finder -> "book 1" (saved estimate)
  -> receipt/final bill -> After-Care Organizer -> optional benefits check
  -> guarded clinic QR payment OR approved reimbursement -> next-care planning

It also runs the visit follow-up ("Did you go to your visit today?") on a timer,
watched by Sentry Crons, and applies Case Medic actions.

State lives in ctx.storage (one dict per case). Durable data lives in Tiger Data
through the Core API.
"""
import asyncio
import re
import time
import yaml
from contextvars import ContextVar
from contextlib import asynccontextmanager
from uuid import uuid4

import sentry_sdk
from sentry_sdk.crons import monitor
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, ResourceContent, chat_protocol_spec,
)

from common.chat import ack, advertise_attachments, say, text_of, upload_resources
from common.attachments import AttachmentError
from common.config import ADDR, BACKEND_ROOT, FOLLOWUP_MINUTES, MODE, PORTS, READMES, require_seed
from common.core import core_get, core_post
from common.conversation import SCOPE_REPLY, care_request, clinical_advice_request, normalize_request, payment_status as document_payment_status, quick_reply
from common.models import (
    AfterCareRequest,
    AfterCareResult,
    CareOptions,
    FindCareRequest,
    InboundText,
    MedicAction,
    OutboundText,
    ScreenRequest,
    ScreenResult,
    SettlementRequest,
    SettlementResult,
    dump,
)
from common.photon_copy import benefits as photon_benefits
from common.photon_copy import booking_saved as photon_booking_saved
from common.photon_copy import care_matches as photon_care_matches
from common.photon_copy import organized_bill as photon_organized_bill
from common.screen_links import screen_for, with_screen_link
from common.safety import first_matching_rule
from common.tracing import carry, case_hash, case_scope, case_span, init_sentry, metric

init_sentry("coordinator")
SAFETY_RULES = yaml.safe_load((BACKEND_ROOT / "rules/red_flags.yaml").read_text())["rules"]

agent = Agent(
    name="Billo",
    seed=require_seed("coordinator"),
    port=PORTS["coordinator"],
    mailbox=True,
    publish_agent_details=True,
    handle_messages_concurrently=True,
    readme_path=str(READMES / "coordinator.md"),
    description=(
        "Billo provides location-matched demo care estimates, organizes bills and receipts, and "
        "explains possible benefit paths and next steps with safety first."
    ),
)

BILL_WORDS = ("bill", "invoice", "statement", "receipt", "charged", "owe")
QR_WORDS = ("visa qr", "clinic qr", "scan qr", "scan to pay", "payment qr")
DONE_WORDS = ("they did", "gave me", "x-ray", "xray", "splint", "brace", "shot", "stitches")
# Core expires active mutation grants after five minutes. Coordinator waits an
# additional margin before reconciling, so clock skew or a just-admitted Core
# write cannot race local timeout recovery.
OPERATION_TIMEOUT_SECONDS = 330

BILLO_ASI_ONE_URL = "https://asi1.ai/ai/agent1qdral3yqhqaa28czja8ddwf7kzgj4evwmpd39qjz3zuxwc64tucyus67y0z"
GROUP_PRIVATE_REPLY = (
    "For privacy, I can’t access or change a personal Billo case in a group chat. "
    "That includes saving a care plan, sharing private case links, logging a visit, reviewing a bill or receipt, "
    "checking case-specific benefits, handling a payment or reimbursement, or creating a WhatsApp handoff. "
    "Start a one-to-one chat with Billo in ASI:One, then resend the request or attachment there: "
    f"{BILLO_ASI_ONE_URL}\n"
    "I did not change a case or process a document or payment from this group message."
)
GROUP_WELCOME = (
    "In this group chat, I can provide emergency safety guidance, general healthcare-cost education, "
    "and public demo care options when the service and city or ZIP code are included in the same message. "
    "I won’t access or change a personal case here. For booking, visit updates, documents, benefits, payments, "
    "reimbursements, or handoffs, start a one-to-one chat with Billo in ASI:One: "
    f"{BILLO_ASI_ONE_URL}"
)

# The Coordinator handles messages concurrently. A case can be open in ASI:One
# and WhatsApp at the same time, so the reply destination belongs to the current
# inbound task rather than to mutable case state.
_REPLY_TARGET: ContextVar[tuple[str, str] | None] = ContextVar("billo_reply_target", default=None)
_GROUP_REPLY: ContextVar[bool] = ContextVar("billo_group_reply", default=False)
_TURN_ARRIVAL: ContextVar[int] = ContextVar("billo_turn_arrival", default=0)
_OPERATION_STATE_LOCKS: dict[str, asyncio.Lock] = {}
_CASE_TURN_GENERATIONS: dict[str, int] = {}
_CASE_EMERGENCY_GENERATIONS: dict[str, int] = {}
_CASE_PRIORITY_INGRESS_GENERATIONS: dict[str, int] = {}
_CASE_PRIORITY_COMPLETED_GENERATIONS: dict[str, int] = {}
_CASE_PENDING_TURNS: dict[str, dict[int, int]] = {}
_CASE_TURN_CONDITIONS: dict[str, asyncio.Condition] = {}
_ACTIVE_CASE_TURNS: dict[str, asyncio.Task] = {}
_ACTIVE_CASE_TURN_LEVELS: dict[str, int] = {}
_DOOR_TURN_LOCKS: dict[str, asyncio.Lock] = {}
_DOOR_TURN_GENERATIONS: dict[str, int] = {}
_DOOR_PRIORITY_GENERATIONS: dict[str, int] = {}
_DOOR_EMERGENCY_GENERATIONS: dict[str, int] = {}
_DOOR_EMERGENCY_COMPLETED_GENERATIONS: dict[str, int] = {}
_DOOR_PENDING_TURNS: dict[str, dict[int, int]] = {}
_DOOR_TURN_CONDITIONS: dict[str, asyncio.Condition] = {}
_ACTIVE_DOOR_TURNS: dict[str, asyncio.Task] = {}
_ACTIVE_DOOR_TURN_LEVELS: dict[str, int] = {}
_CASE_SUPERSEDING_USER_ARRIVALS: dict[str, int] = {}
_ACTIVE_RESULT_TURNS: dict[str, asyncio.Task] = {}
_COMMITTED_RESULT_TURNS: set[str] = set()
_ACTIVE_FOLLOWUP_TURNS: dict[str, asyncio.Task] = {}
_TURN_SEQUENCE = 0


def _operation_state_lock(case_id: str) -> asyncio.Lock:
    """Serialize the Core-start/local-pending handoff for one case."""
    lock = _OPERATION_STATE_LOCKS.get(case_id)
    if lock is None:
        lock = asyncio.Lock()
        _OPERATION_STATE_LOCKS[case_id] = lock
    return lock


def _next_turn_sequence() -> int:
    """Return a restart-stable, strictly increasing ingress timestamp."""
    global _TURN_SEQUENCE
    # Pending generations are persisted with a case. A process-local counter
    # would reset after deployment and could make a newer user turn look older
    # than an operation started by the previous process.
    _TURN_SEQUENCE = max(_TURN_SEQUENCE + 1, time.time_ns())
    return _TURN_SEQUENCE


def _register_case_turn(case_id: str, generation: int | None = None,
                        *, priority: bool = False, emergency: bool = False) -> int:
    generation = _next_turn_sequence() if generation is None else generation
    priority = priority or emergency
    level = 2 if emergency else 1 if priority else 0
    _CASE_TURN_GENERATIONS[case_id] = max(
        generation, _CASE_TURN_GENERATIONS.get(case_id, 0),
    )
    pending = _CASE_PENDING_TURNS.setdefault(case_id, {})
    pending[generation] = max(level, pending.get(generation, 0))
    if priority:
        _CASE_PRIORITY_INGRESS_GENERATIONS[case_id] = max(
            generation, _CASE_PRIORITY_INGRESS_GENERATIONS.get(case_id, 0),
        )
    current = asyncio.current_task()
    if emergency:
        _CASE_EMERGENCY_GENERATIONS[case_id] = max(
            generation, _CASE_EMERGENCY_GENERATIONS.get(case_id, 0),
        )
    active = _ACTIVE_CASE_TURNS.get(case_id)
    active_level = _ACTIVE_CASE_TURN_LEVELS.get(case_id, 0)
    # Higher-severity work preempts lower-severity work. Equal-severity turns
    # remain FIFO, and STOP can therefore never cancel an active 911 response.
    if (
        priority and active is not None and active is not current
        and not active.done() and level > active_level
    ):
        active.cancel()
    return generation


@asynccontextmanager
async def _case_turn(case_id: str, generation: int, *, priority: bool = False,
                     emergency: bool = False):
    """Run case work FIFO, with emergency > STOP > ordinary priority."""
    priority = priority or emergency
    requested_level = 2 if emergency else 1 if priority else 0
    pending = _CASE_PENDING_TURNS.setdefault(case_id, {})
    pending[generation] = max(requested_level, pending.get(generation, 0))
    condition = _CASE_TURN_CONDITIONS.get(case_id)
    if condition is None:
        condition = asyncio.Condition()
        _CASE_TURN_CONDITIONS[case_id] = condition
    current = asyncio.current_task()
    cleaned = False
    try:
        async with condition:
            # Registration is synchronous; notifying here wakes turns that were
            # waiting when a higher-priority arrival changed the queue.
            condition.notify_all()
            while True:
                level = pending.get(generation)
                if level is None:
                    yield False
                    return
                newer_higher = any(
                    other_generation > generation and other_level > level
                    for other_generation, other_level in pending.items()
                )
                latest_priority = _CASE_PRIORITY_INGRESS_GENERATIONS.get(case_id, 0)
                if newer_higher or (level == 0 and generation < latest_priority):
                    pending.pop(generation, None)
                    if level:
                        _CASE_PRIORITY_COMPLETED_GENERATIONS[case_id] = max(
                            generation, _CASE_PRIORITY_COMPLETED_GENERATIONS.get(case_id, 0),
                        )
                    cleaned = True
                    condition.notify_all()
                    yield False
                    return
                highest_level = max(pending.values(), default=level)
                first_at_level = min(
                    queued_generation
                    for queued_generation, queued_level in pending.items()
                    if queued_level == highest_level
                )
                if level == highest_level and generation == first_at_level:
                    break
                await condition.wait()
            if current is not None:
                _ACTIVE_CASE_TURNS[case_id] = current
                _ACTIVE_CASE_TURN_LEVELS[case_id] = level
            try:
                yield True
            finally:
                if level:
                    _CASE_PRIORITY_COMPLETED_GENERATIONS[case_id] = max(
                        generation, _CASE_PRIORITY_COMPLETED_GENERATIONS.get(case_id, 0),
                    )
                pending.pop(generation, None)
                cleaned = True
                if current is not None and _ACTIVE_CASE_TURNS.get(case_id) is current:
                    _ACTIVE_CASE_TURNS.pop(case_id, None)
                    _ACTIVE_CASE_TURN_LEVELS.pop(case_id, None)
                condition.notify_all()
    finally:
        # A task can be cancelled while waiting on the condition, before it has
        # reached the yielded context. Always remove that queue entry.
        if not cleaned and generation in pending:
            async with condition:
                level = pending.pop(generation, 0)
                if level:
                    _CASE_PRIORITY_COMPLETED_GENERATIONS[case_id] = max(
                        generation, _CASE_PRIORITY_COMPLETED_GENERATIONS.get(case_id, 0),
                    )
                condition.notify_all()


async def _abandon_case_turn(case_id: str, generation: int) -> None:
    """Remove an ingress that failed before it could enter the case queue."""
    pending = _CASE_PENDING_TURNS.get(case_id)
    if not pending or generation not in pending:
        return
    condition = _CASE_TURN_CONDITIONS.get(case_id)
    if condition is None:
        condition = asyncio.Condition()
        _CASE_TURN_CONDITIONS[case_id] = condition
    async with condition:
        level = pending.pop(generation, 0)
        if level:
            _CASE_PRIORITY_COMPLETED_GENERATIONS[case_id] = max(
                generation, _CASE_PRIORITY_COMPLETED_GENERATIONS.get(case_id, 0),
            )
        condition.notify_all()


def _register_door_turn(door: str, generation: int | None = None,
                        *, priority: bool = False, emergency: bool = False) -> int:
    """Register arrival before the first await so a later emergency can preempt."""
    generation = _next_turn_sequence() if generation is None else generation
    priority = priority or emergency
    level = 2 if emergency else 1 if priority else 0
    _DOOR_TURN_GENERATIONS[door] = max(
        generation, _DOOR_TURN_GENERATIONS.get(door, 0),
    )
    pending = _DOOR_PENDING_TURNS.setdefault(door, {})
    pending[generation] = max(level, pending.get(generation, 0))
    if priority:
        _DOOR_PRIORITY_GENERATIONS[door] = max(
            generation, _DOOR_PRIORITY_GENERATIONS.get(door, 0),
        )
    current = asyncio.current_task()
    if emergency:
        _DOOR_EMERGENCY_GENERATIONS[door] = max(
            generation, _DOOR_EMERGENCY_GENERATIONS.get(door, 0),
        )
    active = _ACTIVE_DOOR_TURNS.get(door)
    active_level = _ACTIVE_DOOR_TURN_LEVELS.get(door, 0)
    if (
        priority and active is not None and active is not current
        and not active.done() and level > active_level
    ):
        active.cancel()
    return generation


@asynccontextmanager
async def _door_turn(door: str, generation: int, *, priority: bool = False,
                     emergency: bool = False):
    priority = priority or emergency
    requested_level = 2 if emergency else 1 if priority else 0
    pending = _DOOR_PENDING_TURNS.setdefault(door, {})
    pending[generation] = max(requested_level, pending.get(generation, 0))
    condition = _DOOR_TURN_CONDITIONS.get(door)
    if condition is None:
        condition = asyncio.Condition()
        _DOOR_TURN_CONDITIONS[door] = condition
    current = asyncio.current_task()
    cleaned = False
    try:
        async with condition:
            condition.notify_all()
            while True:
                level = pending.get(generation)
                if level is None:
                    yield False
                    return
                newer_higher = any(
                    other_generation > generation and other_level > level
                    for other_generation, other_level in pending.items()
                )
                latest_priority = _DOOR_PRIORITY_GENERATIONS.get(door, 0)
                if newer_higher or (level == 0 and generation < latest_priority):
                    pending.pop(generation, None)
                    if level:
                        _DOOR_EMERGENCY_COMPLETED_GENERATIONS[door] = max(
                            generation, _DOOR_EMERGENCY_COMPLETED_GENERATIONS.get(door, 0),
                        )
                    cleaned = True
                    condition.notify_all()
                    yield False
                    return
                highest_level = max(pending.values(), default=level)
                first_at_level = min(
                    queued_generation
                    for queued_generation, queued_level in pending.items()
                    if queued_level == highest_level
                )
                if level == highest_level and generation == first_at_level:
                    break
                await condition.wait()
            if current is not None:
                _ACTIVE_DOOR_TURNS[door] = current
                _ACTIVE_DOOR_TURN_LEVELS[door] = level
            try:
                yield True
            finally:
                if level:
                    _DOOR_EMERGENCY_COMPLETED_GENERATIONS[door] = max(
                        generation, _DOOR_EMERGENCY_COMPLETED_GENERATIONS.get(door, 0),
                    )
                pending.pop(generation, None)
                cleaned = True
                if current is not None and _ACTIVE_DOOR_TURNS.get(door) is current:
                    _ACTIVE_DOOR_TURNS.pop(door, None)
                    _ACTIVE_DOOR_TURN_LEVELS.pop(door, None)
                condition.notify_all()
    finally:
        if not cleaned and generation in pending:
            async with condition:
                level = pending.pop(generation, 0)
                if level:
                    _DOOR_EMERGENCY_COMPLETED_GENERATIONS[door] = max(
                        generation, _DOOR_EMERGENCY_COMPLETED_GENERATIONS.get(door, 0),
                    )
                condition.notify_all()


async def _abandon_door_turn(door: str, generation: int) -> None:
    """Remove an ingress whose acknowledgement failed before processing."""
    pending = _DOOR_PENDING_TURNS.get(door)
    if not pending or generation not in pending:
        return
    condition = _DOOR_TURN_CONDITIONS.get(door)
    if condition is None:
        condition = asyncio.Condition()
        _DOOR_TURN_CONDITIONS[door] = condition
    async with condition:
        level = pending.pop(generation, 0)
        if level:
            _DOOR_EMERGENCY_COMPLETED_GENERATIONS[door] = max(
                generation, _DOOR_EMERGENCY_COMPLETED_GENERATIONS.get(door, 0),
            )
        condition.notify_all()


def _reload_case(ctx: Context | None, case: dict) -> dict:
    """Reload after waiting for a case lock; test contexts may have no storage."""
    if ctx is not None and getattr(ctx, "storage", None) is not None:
        return load(ctx, case["id"]) or case
    return case


def _current_turn_arrival(case_id: str) -> int:
    arrival_var = globals().get("_TURN_ARRIVAL")
    arrival = int(arrival_var.get() or 0) if arrival_var is not None else 0
    return arrival or _CASE_TURN_GENERATIONS.get(case_id, 0)


def location_hint(text: str) -> str | None:
    """Extract a location update that the demo catalog can resolve."""
    low = text.lower()
    if re.search(r"\b(chicago|606\d{2})\b", low):
        return "Chicago, IL"
    if re.search(r"\b(los angeles|ucla|westwood|900\d{2})\b", low):
        return "Los Angeles, CA"
    match = re.search(
        r"\b(?:i(?:'m| am)\s+(?:now\s+|currently\s+)?in|(?:now|currently)\s+in|"
        r"near|around|location(?: is)?|zip(?: code)?(?: is)?)\s+([^,.;!?]+)",
        text,
        re.I,
    )
    if not match:
        return None
    candidate = match.group(1).strip()
    return None if candidate.lower() in {"me", "here", "my area"} else candidate


def _priority_turn(text: str) -> tuple[bool, bool]:
    """Return (priority, emergency) without awaiting or touching case state."""
    emergency = bool(first_matching_rule(text, SAFETY_RULES))
    clean = re.sub(r"[!?. ,]+$", "", normalize_request(text).lower().strip())
    return emergency or clean == "stop", emergency


def _turn_supersedes_recovered_reply(case: dict, text: str, *, has_attachment: bool = False,
                                      attachment_error: str = "") -> bool:
    """True when the current action should own the response, not an old job."""
    if has_attachment or attachment_error:
        return True
    low = normalize_request(text).lower().strip()
    if (
        low.startswith(("approve clinic payment", "approve reimbursement"))
        or any(word in low for word in QR_WORDS)
        or any(word in low for word in (
            "hsa", "fsa", "hra", "out of network", "out-of-network", "employer benefit",
            "student benefit", "travel insurance", "accident insurance", "check benefits",
        ))
        or re.fullmatch(
            r"(?:book|pick|choose|save)(?:\s+(?:option|number|provider))?\s*#?\s*\d+.*",
            low,
        )
    ):
        return True
    if case.get("stage") in {"booked", "during"} and any(word in low for word in DONE_WORDS):
        return True
    return bool(location_hint(text) or care_request(text, has_prior=bool(case.get("care_query"))))


def _record_superseding_ingress(ctx: Context | None, door: str, arrival: int,
                                text: str, *, priority: bool = False,
                                explicit_case_id: str = "", has_attachment: bool = False,
                                attachment_error: str = "") -> str:
    """Mark a queued user action before any await so old results stay silent."""
    storage = getattr(ctx, "storage", None)
    if storage is None:
        return ""
    case_id = explicit_case_id or str(storage.get(door) or "")
    if not case_id:
        return ""
    case = load(ctx, case_id)
    if not case:
        return ""
    # A user message always owns the conversation ahead of a timer reminder.
    active_followup = _ACTIVE_FOLLOWUP_TURNS.get(case_id)
    if active_followup is not None and not active_followup.done():
        active_followup.cancel()
    superseding = priority or _turn_supersedes_recovered_reply(
        case, text, has_attachment=has_attachment, attachment_error=attachment_error,
    )
    if superseding:
        _CASE_SUPERSEDING_USER_ARRIVALS[case_id] = max(
            arrival, _CASE_SUPERSEDING_USER_ARRIVALS.get(case_id, 0),
        )
    if priority:
        _CASE_PRIORITY_INGRESS_GENERATIONS[case_id] = max(
            arrival, _CASE_PRIORITY_INGRESS_GENERATIONS.get(case_id, 0),
        )
    active_result = _ACTIVE_RESULT_TURNS.get(case_id)
    if (
        active_result is not None and not active_result.done()
        and (priority or case_id in _COMMITTED_RESULT_TURNS)
    ):
        active_result.cancel()
    return case_id


def _associate_priority_case(hinted_case_id: str, resolved_case_id: str,
                             arrival: int, *, priority: bool) -> None:
    if not priority:
        return
    if hinted_case_id and hinted_case_id != resolved_case_id:
        _CASE_PRIORITY_COMPLETED_GENERATIONS[hinted_case_id] = max(
            arrival, _CASE_PRIORITY_COMPLETED_GENERATIONS.get(hinted_case_id, 0),
        )
    _CASE_PRIORITY_INGRESS_GENERATIONS[resolved_case_id] = max(
        arrival, _CASE_PRIORITY_INGRESS_GENERATIONS.get(resolved_case_id, 0),
    )


# ------------------------------------------------------------------ case state
def _key(channel: str, who: str) -> str:
    return f"door:{channel}:{who}"


def _group_target_key(channel: str, who: str) -> str:
    """Remember group destinations without attaching them to a private case."""
    return f"group-target:{channel}:{who}"


def _is_group_target(ctx: Context | None, case: dict, target: tuple[str, str] | list[str]) -> bool:
    group_var = globals().get("_GROUP_REPLY")
    if group_var is not None and group_var.get():
        return True
    channel, who = tuple(target)
    if case.get("is_group"):
        return True
    storage = getattr(ctx, "storage", None)
    return bool(storage and storage.get(_group_target_key(channel, who)))


def _group_context(channel: str, who: str) -> dict:
    """Return an unsaved context for public guidance in a group conversation."""
    return {
        "id": uuid4().hex[:12], "channel": channel, "who": who, "stage": "new",
        "places": [], "after_care": None, "benefits": [], "settlement": None,
        "flags": {}, "followup_due": 0, "asked": False, "is_group": True,
    }


def get_case(ctx: Context, channel: str, who: str) -> dict:
    case_id = ctx.storage.get(_key(channel, who))
    if case_id and ctx.storage.get(f"case:{case_id}"):
        # Recovery mutates case state and therefore belongs inside _case_turn.
        return ctx.storage.get(f"case:{case_id}")
    case = {"id": uuid4().hex[:12], "channel": channel, "who": who, "stage": "new",
            "places": [], "after_care": None, "benefits": [], "settlement": None,
            "flags": {}, "followup_due": 0, "asked": False}
    save(ctx, case)
    ctx.storage.set(_key(channel, who), case["id"])
    return case


def new_case(ctx: Context, channel: str, who: str) -> dict:
    """Start a separate care case without merging records from a completed one."""
    case = {
        "id": uuid4().hex[:12], "channel": channel, "who": who, "stage": "new",
        "places": [], "after_care": None, "benefits": [], "settlement": None,
        "flags": {}, "followup_due": 0, "asked": False,
        "last_target": [channel, who], "destinations": {channel: who},
    }
    save(ctx, case)
    ctx.storage.set(_key(channel, who), case["id"])
    return case


def load(ctx: Context, case_id: str) -> dict | None:
    """Find a case by its id, or by the keyed hash Sentry and Case Medic see."""
    case = ctx.storage.get(f"case:{case_id}")
    if case is None and case_id:
        real = ctx.storage.get(f"hash:{case_id}")
        case = ctx.storage.get(f"case:{real}") if real else None
    return case


def _recover_interrupted_operations(case: dict, *, now: float | None = None) -> bool:
    """Recover only pre-correlation cases; timed work needs Core reconciliation."""
    after_id = str(case.get("pending_after_care_id") or "")
    if case.get("stage") == "organizing" and not after_id:
        case.pop("pending_after_care_id", None)
        case.pop("pending_after_care_generation", None)
        case.pop("pending_after_care_target", None)
        case.pop("pending_after_care_started_at", None)
        case["stage"] = case.pop(
            "stage_before_organizing", "organized" if case.get("after_care") else "new"
        )
        return True
    return False


# Stages that are safe to count in Sentry. "emergency" is health data, so it is never a metric.
METRIC_STAGES = {"new", "choosing", "booked", "during", "organizing", "organized", "settled"}

# Sentry Crons: the follow-up timer must check in every minute or Sentry raises an issue.
FOLLOWUP_MONITOR = {
    "schedule": {"type": "interval", "value": 1, "unit": "minute"},
    "checkin_margin": 2,          # minutes late before "missed"
    "max_runtime": 1,             # minutes before "timed out"
    "failure_issue_threshold": 2,
    "recovery_threshold": 1,
}


def save(ctx: Context, case: dict) -> None:
    # Migrate legacy state and enforce the bearer-at-rest boundary centrally.
    # Any private URL is reissued by authenticated Core only for an outbound
    # response; Coordinator storage retains only the fact that a case view exists.
    if case.pop("visit_url", ""):
        case["case_link_ready"] = True
    if isinstance(case.get("settlement"), dict):
        for key in ("handoff_url", "wallet_api_url"):
            case["settlement"].pop(key, None)
    if case.get("stage") != case.get("_metric_stage"):
        case["_metric_stage"] = case.get("stage")
        if case.get("stage") in METRIC_STAGES:
            metric("count", "billo.case.stage", stage=case["stage"], channel=case.get("channel", ""))
    ctx.storage.set(f"case:{case['id']}", case)
    ctx.storage.set(f"hash:{case_hash(case['id'])}", case["id"])
    ids = set(ctx.storage.get("case_ids") or [])
    ids.add(case["id"])
    ctx.storage.set("case_ids", sorted(ids))


async def reply(ctx: Context, case: dict, text: str, *, photon_text: str | None = None,
                target: tuple[str, str] | list[str] | None = None,
                group_safe: bool = False, private_visit_url: str = "",
                supersession_generation: int = 0) -> None:
    """Send on the inbound task's channel, even when one case has two channels."""
    def superseded() -> bool:
        return bool(
            supersession_generation
            and _CASE_SUPERSEDING_USER_ARRIVALS.get(case["id"], 0) > supersession_generation
        )

    if superseded():
        return
    target_var = globals().get("_REPLY_TARGET")
    scoped = target_var.get() if target_var is not None else None
    remembered = case.get("last_target")
    channel, who = tuple(target or scoped or remembered or (case["channel"], case["who"]))
    group_target = group_safe or _is_group_target(ctx, case, (channel, who))
    if group_target and not group_safe:
        # Delayed results and reminders can outlive the inbound task. If their
        # destination is a group, replace all case content with the privacy gate.
        text = GROUP_PRIVATE_REPLY
        photon_text = GROUP_PRIVATE_REPLY
    if group_target:
        detailed = text
        compact = photon_text or text
    else:
        # Public case URLs are bearer credentials. Keep them in the outbound
        # response only, never in uAgents case storage. Core deterministically
        # reissues the same scoped URL from its hash-only token registry.
        visit_url = private_visit_url
        stage = case.get("stage", "new")
        needs_screen = bool(
            screen_for(text, stage) or screen_for(photon_text or text, stage)
        )
        low = text.lower().strip()
        urgent_or_stopped = (
            "call 911" in low or "988" in low
            or low.startswith(("stopped", "✅ stopped", "you are unsubscribed"))
        )
        if (
            not visit_url and case.get("case_link_ready")
            and needs_screen and not urgent_or_stopped
        ):
            try:
                visit_url = str((await core_post(
                    "/case-links", {"case_id": case["id"]},
                )).get("visit_url") or "")
            except Exception:
                sentry_sdk.capture_message("private case link could not be issued", level="warning")
            if superseded():
                return
        detailed = with_screen_link(text, stage, visit_url)
        compact = with_screen_link(photon_text or text, stage, visit_url)
    if superseded():
        return
    if channel == "asi1":
        await say(ctx, who, detailed)
    elif channel in {"imessage", "sms", "whatsapp_business"} and ADDR["gateway"]:
        await ctx.send(ADDR["gateway"], OutboundText(
            space_id=who, text=compact, case_id="" if group_target else case["id"], trace=carry()))


def _general_group_explanation(text: str, immediate: str | None) -> bool:
    """Allow only known, case-independent educational quick replies in groups."""
    if immediate is None:
        return False
    clean = re.sub(r"[!?. ,]+$", "", text.lower().replace("’", "'").strip())
    return bool(
        re.fullmatch(
            r"what is (?:a |an )?(?:deductible|copay|coinsurance|eob|itemized bill|"
            r"prior authorization|in network|out of network|balance billing|good faith estimate)",
            clean,
        )
        or clean in {"can you guarantee reimbursement", "is my information private"}
    )


def _group_private_action(text: str, files: list[str], attachment_error: str = "") -> bool:
    """Conservatively identify actions that must never run against a group."""
    if files or attachment_error:
        return True
    low = text.lower().replace("’", "'").strip()
    if low in {
        "yes", "y", "no", "n", "not yet", "i went", "yes i went", "stop",
        "status", "my status", "what next", "what's next", "this is paid",
        "this is unpaid", "it is paid", "it is unpaid",
    }:
        return True
    # “X-ray in Chicago” is a public care search; a bare X-ray update in an
    # existing group conversation is an unsafe visit-log attempt.
    if re.search(r"\bx-?ray\b", low) and not location_hint(text):
        return True
    return bool(re.search(
        r"\b(?:book(?:ing)?|pick|choose|save|reserve|select|case|care plan|private link|"
        r"visit log|follow[ -]?up|reminder|they did|gave me|splint|brace|shot|stitches|"
        r"bill|invoice|statement|receipt|charged?|owe|document|upload|attach|photo|pdf|"
        r"benefits?|coverage|insurance|claim|hsa|fsa|hra|out[ -]?of[ -]?network|"
        r"pay|payment|wallet|visa|qr|reimburs\w*|refund|settle\w*|"
        r"whatsapp|handoff|link code)\b",
        low,
    ))


async def step_group_guidance(ctx: Context, case: dict, text: str) -> None:
    """Give stateless safety and public care guidance without touching a case."""
    requested_location = location_hint(text)
    res, _ = await ctx.send_and_receive(
        ADDR["red_flag"], ScreenRequest(case_id=case["id"], text=text, trace=carry()),
        response_type=ScreenResult, timeout=20,
    )
    if res is None:
        await reply(
            ctx, case,
            "I couldn’t complete the safety check, so I won’t suggest care options. "
            "If this may be an emergency, call 911 now; otherwise, try again in a moment.",
            group_safe=True,
        )
        return
    if res.emergency:
        await reply(ctx, case, res.message, group_safe=True)
        return
    if clinical_advice_request(text):
        await reply(ctx, case, (
            "I can provide general care-finding and cost information, but I can’t diagnose, prescribe, "
            "or recommend a medication dose. Ask a licensed clinician or pharmacist. For a public care "
            "comparison here, include the service and city or ZIP code in one message."
        ), group_safe=True)
        return
    if not requested_location or not care_request(text):
        await reply(ctx, case, (
            "Safety check: no emergency indicators were found in your message. For a public demo care "
            "comparison, include both the service and city or ZIP code in one message—for example, "
            "‘knee X-ray in Chicago.’ Group requests are not saved to a personal Billo case."
        ), group_safe=True)
        return
    opts, _ = await ctx.send_and_receive(
        ADDR["care_finder"], FindCareRequest(
            case_id=case["id"], text=text, near=requested_location, group_safe=True, trace=carry(),
        ),
        response_type=CareOptions, timeout=30,
    )
    if opts is None:
        await reply(
            ctx, case,
            "I couldn’t load public demo care options right now. No personal case was created or changed; please try again in a moment.",
            group_safe=True,
        )
        return
    location = opts.location or requested_location
    if not opts.places:
        await reply(ctx, case, (
            f"I don’t have verified demo care options for {location}. Try another city or ZIP code. "
            "No personal case was created or changed."
        ), group_safe=True)
        return
    lines = [
        "Safety check: no emergency indicators were found in your message.",
        f"Public demo care options in {location}:",
    ]
    for i, place in enumerate(opts.places, 1):
        lines.append(
            f"{i}. {place.name}\n"
            f"   Type: {place.kind.replace('_', ' ').title()}\n"
            f"   Estimated price: ${place.price_typical:,.0f} (from ${place.price_low:,.0f})\n"
            f"   Location: {place.address}\n"
            f"   Availability: {place.hours}\n"
            f"   Data source: {place.price_source}"
        )
    lines.extend([
        "These are public demo estimates, not live quotes. Confirm price and availability directly with the provider.",
        "I did not save a care plan or create a private case link from this group message.",
        f"To save an option, continue in a one-to-one Billo chat: {BILLO_ASI_ONE_URL}",
    ])
    await reply(ctx, case, "\n".join(lines), group_safe=True)


# ------------------------------------------------------------------ steps
async def step_symptoms(ctx: Context, case: dict, text: str, group_safe: bool = False) -> None:
    requested_location = location_hint(text)
    if requested_location:
        case["near"] = requested_location
    near = case.get("near", "UCLA, Los Angeles, CA")
    prior_query = case.get("care_query", "")
    if requested_location and not prior_query and not care_request(text):
        save(ctx, case)
        await reply(
            ctx,
            case,
            f"Location saved: {near}. What care do you need help finding? Describe the symptom or service so I can run the safety check before showing options.",
        )
        return
    care_query = f"{prior_query}. Current location: {near}" if requested_location and prior_query else text
    if not (requested_location and prior_query):
        case["care_query"] = text
    res, _ = await ctx.send_and_receive(
        ADDR["red_flag"], ScreenRequest(case_id=case["id"], text=text, trace=carry()),
        response_type=ScreenResult, timeout=20)
    if res is None:
        await reply(ctx, case, "I couldn’t complete the safety check. I won’t recommend care options without it. If this may be an emergency, call 911 now; otherwise, please try again in a moment.")
        return
    if res.emergency:
        case["stage"] = "emergency"
        save(ctx, case)
        await reply(ctx, case, res.message)
        return
    if clinical_advice_request(text):
        await reply(ctx, case, (
            "I can help you find care and understand costs, but I can’t diagnose, prescribe, or recommend a medication dose. "
            "Please ask a licensed clinician or pharmacist. Tell me your city or ZIP code if you’d like help comparing care options."
        ))
        return
    if not requested_location and not case.get("near"):
        save(ctx, case)
        await reply(ctx, case, "Which city or ZIP code should I search? I saved your care request and won’t assume your location.")
        return
    opts, _ = await ctx.send_and_receive(
        ADDR["care_finder"], FindCareRequest(
            case_id=case["id"], text=care_query, near=near, group_safe=group_safe, trace=carry()),
        response_type=CareOptions, timeout=30)
    if opts is None:
        await reply(ctx, case, "I couldn’t load care options right now. Your previous options were not changed. Please try again in a moment.")
        return
    case["places"] = [dump(p) for p in opts.places]
    case["code"] = opts.code
    case["location"] = opts.location or near
    case["data_mode"] = opts.data_mode
    if not opts.places:
        case["stage"] = "new"
        save(ctx, case)
        await reply(ctx, case, (
            f"Location updated: {case['location']}. I don’t have verified demo options for that area yet, so I cleared the previous location’s results. "
            "Try another city or ZIP code."
        ), photon_text=photon_care_matches([], case["location"]))
        return
    case["stage"] = "choosing"
    save(ctx, case)
    # TODO(cards): send this as an ASI1 Interactive Card carousel (see AGENTS.md)
    lines = [
        "Safety check: no emergency indicators were found in your message.",
        f"Location: {case['location']}",
        f"Care options ({len(opts.places)}):",
    ]
    for i, p in enumerate(opts.places, 1):
        lines.append(
            f"{i}. {p.name}\n"
            f"   Type: {p.kind.replace('_', ' ').title()}\n"
            f"   Estimated price: ${p.price_typical:,.0f} (from ${p.price_low:,.0f})\n"
            f"   Location: {p.address}\n"
            f"   Availability: {p.hours}\n"
            f"   Data source: {p.price_source}"
        )
    lines.append("Next step: reply ‘book 1,’ ‘book 2,’ or ‘book 3’ to save an option and estimate.")
    lines.append("Important: these are demo estimates, not live quotes. Saving an option does not confirm an appointment; verify price and availability directly with the provider.")
    await reply(
        ctx,
        case,
        "\n".join(lines),
        photon_text=photon_care_matches(case["places"], case["location"]),
    )


async def step_book(ctx: Context, case: dict, n: int) -> None:
    if not (1 <= n <= len(case["places"])):
        choices = ", ".join(f"{i}. {place['name']}" for i, place in enumerate(case["places"], 1))
        await reply(ctx, case, f"That option number isn’t available. Choose one of these options: {choices}.")
        return
    place = case["places"][n - 1]
    est = await core_post("/estimates", {
        "case_id": case["id"], "npi": place["npi"], "place": place["name"],
        "code": case.get("code", ""), "amount": place["price_typical"],
        "address": place.get("address", ""), "hours": place.get("hours", ""),
        "source_label": place.get("price_source", ""),
        "data_mode": case.get("data_mode", "demo"),
    })
    case_link = await core_post("/case-links", {"case_id": case["id"]})
    link = await core_post("/link-codes", {
        "case_id": case["id"], "channel": "whatsapp_business",
    })
    visit_url = case_link["visit_url"]
    calendar_url = str(case_link.get("ics_url") or est.get("ics_url") or "")
    google_calendar_url = str(case_link.get("gcal_url") or est.get("gcal_url") or "")
    deep_link = str(link.get("deep_link") or "")
    # A partial Core response must fail closed: both transport availability and
    # a usable provider deep link are required before advertising WhatsApp.
    handoff_available = link.get("available") is True and bool(deep_link)
    handoff_page = str(link.get("case_page") or "")
    case.update(
        stage="booked", place=place, gfe=est["amount"], case_link_ready=True,
        followup_due=time.time() + FOLLOWUP_MINUTES * 60, asked=False,
    )
    save(ctx, case)
    handoff_text = (
        f"\nTo continue this same case in WhatsApp, open the secure handoff: {handoff_page}"
        if handoff_available and handoff_page else ""
    )
    calendar_text = (
        f"Calendar reminder: {calendar_url}\nGoogle Calendar: {google_calendar_url}\n\n"
        if calendar_url and google_calendar_url else
        "No appointment time was added. After the provider confirms a time, add that confirmed appointment to your calendar.\n\n"
    )
    await reply(ctx, case, (
        f"Care plan saved\n"
        f"Provider: {place['name']}\n"
        f"Location: {place['address']}\n"
        f"Availability: {place.get('hours') or 'Confirm directly with the provider'}\n"
        f"Estimated price: ${est['amount']:,.0f}\n\n"
        "This is not a confirmed appointment. Contact the provider to verify availability and the final price.\n\n"
        f"{calendar_text}"
        "During the visit, tell me which services you receive—for example, ‘they did an X-ray’—and I’ll update the running estimate.\n"
        f"{handoff_text}"
    ), photon_text=photon_booking_saved(place, est["amount"], calendar_url, visit_url),
       private_visit_url=visit_url)


async def step_visit_log(ctx: Context, case: dict, text: str) -> None:
    res = await core_post("/visit-events", {"case_id": case["id"], "text": text})
    case["stage"] = "during"
    save(ctx, case)
    await reply(ctx, case, res["say"])


async def step_whatsapp_handoff(ctx: Context, case: dict) -> None:
    """Issue a short-lived channel join without storing its claim credential."""
    link = await core_post("/link-codes", {
        "case_id": case["id"], "channel": "whatsapp_business",
    })
    case_page = str(link.get("case_page") or "")
    configured = link.get("available") is True and bool(link.get("deep_link"))
    if configured and case_page:
        await reply(ctx, case, (
            "WhatsApp handoff ready\n"
            "Open this private, one-time handoff page within 15 minutes:\n"
            f"{case_page}\n"
            "Do not share this link. The code can connect one WhatsApp chat to this case."
        ))
        return
    await reply(ctx, case, (
        "WhatsApp is not configured for Billo yet, so I did not provide a handoff link. "
        "Continue in ASI:One for this case."
    ))


async def step_after_care(ctx: Context, case: dict, file_url: str, payment_status: str, *, demo: bool = False) -> None:
    if not file_url and not demo:
        await reply(ctx, case, "Please attach a clear bill or receipt image or PDF first. I won’t substitute a demo document for a missing upload.")
        return
    previous_stage = case["stage"]
    request_id = uuid4().hex
    await core_post("/operations/start", {
        "case_id": case["id"], "kind": "after_care", "request_id": request_id,
    })
    # Core start is case-wide and atomically supersedes either operation kind.
    # Mirror that decision locally only after Core has accepted the new grant.
    _supersede_pending_operations(case)
    if previous_stage != "organizing":
        case["stage_before_organizing"] = previous_stage
    case["stage"] = "organizing"
    case["pending_after_care_id"] = request_id
    case["pending_after_care_generation"] = _current_turn_arrival(case["id"])
    case["pending_after_care_started_at"] = time.time()
    target_var = globals().get("_REPLY_TARGET")
    current_target = target_var.get() if target_var is not None else None
    if current_target:
        case["pending_after_care_target"] = list(current_target)
    save(ctx, case)
    await reply(
        ctx,
        case,
        "Document received. I’m extracting the provider and charges, then comparing them with your saved care plan. I’ll flag anything that needs review and ask you to confirm an unclear payment status.",
        photon_text="📸 Got it — reading your bill.\nChecking provider, charges + saved estimate.",
    )
    await ctx.send(ADDR["bill_auditor"], AfterCareRequest(
        case_id=case["id"], request_id=request_id, file_url=file_url, demo=demo,
        hospital_npi=(case.get("place") or {}).get("npi", ""), payment_status=payment_status,
        reply_to=str(ctx.agent.address), trace=carry()))


async def step_benefits(ctx: Context, case: dict, text: str) -> None:
    if not case.get("after_care"):
        await reply(ctx, case, "Please attach a paid receipt or final bill first. I need the organized document before I can evaluate a benefit path for the correct visit.")
        return
    result = await core_post("/benefits/check", {"case_id": case["id"], "text": text})
    case["benefits"] = result["paths"]
    save(ctx, case)
    lines = [result["message"]]
    for path in result["paths"]:
        lines.append(f"- {path['name']}: possible, not confirmed. Needed: {path['needed']}.")
    if result["paths"]:
        lines.append("Check each plan's rules and deadline before submitting anything.")
    await reply(
        ctx, case, "\n".join(lines),
        photon_text=photon_benefits(result["paths"]),
    )


async def step_scan_clinic_qr(ctx: Context, case: dict, file_url: str, demo: bool = False) -> None:
    if case.get("stage") == "organizing":
        await reply(ctx, case, "I’m still organizing the current document. Wait for that review to finish before scanning a clinic QR.")
        return
    if not case.get("after_care") or case["after_care"].get("payment_status") != "unpaid":
        await reply(ctx, case, "Please attach and organize the unpaid final bill first. I must verify the provider and exact amount before reviewing a clinic QR.")
        return
    request_id = uuid4().hex
    await core_post("/operations/start", {
        "case_id": case["id"], "kind": "settlement", "request_id": request_id,
    })
    _supersede_pending_operations(case)
    case["pending_settlement_id"] = request_id
    case["pending_settlement_action"] = "inspect_qr"
    case["pending_settlement_generation"] = _current_turn_arrival(case["id"])
    case["pending_settlement_started_at"] = time.time()
    target_var = globals().get("_REPLY_TARGET")
    current_target = target_var.get() if target_var is not None else None
    if current_target:
        case["pending_settlement_target"] = list(current_target)
    save(ctx, case)
    await reply(
        ctx,
        case,
        "QR received. I’m verifying the checksum, network marker, clinic identity, currency, and exact bill amount. This review does not move money.",
        photon_text="🔎 Checking this clinic QR…\nMerchant · amount · currency\nNo money moves yet.",
    )
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], request_id=request_id, action="inspect_qr",
        file_url=file_url, demo=demo,
        reply_to=str(ctx.agent.address), trace=carry()))


async def step_approve_clinic_payment(ctx: Context, case: dict) -> None:
    if case.get("stage") == "organizing":
        await reply(ctx, case, "I’m still organizing the current document. Wait for that review to finish before approving a clinic payment.")
        return
    if case.get("settlement_paused"):
        await reply(ctx, case, "Payment review is paused because a safety check is unresolved. Approval is unavailable, and no money moved.")
        return
    settlement = case.get("settlement") or {}
    if settlement.get("status") != "verified" or not settlement.get("settlement_id"):
        await reply(ctx, case, "Please scan and verify the clinic Visa QR before requesting approval.")
        return
    request_id = uuid4().hex
    await core_post("/operations/start", {
        "case_id": case["id"], "kind": "settlement", "request_id": request_id,
    })
    _supersede_pending_operations(case)
    case["pending_settlement_id"] = request_id
    case["pending_settlement_action"] = "approve_qr"
    case["pending_settlement_generation"] = _current_turn_arrival(case["id"])
    case["pending_settlement_started_at"] = time.time()
    target_var = globals().get("_REPLY_TARGET")
    current_target = target_var.get() if target_var is not None else None
    if current_target:
        case["pending_settlement_target"] = list(current_target)
    save(ctx, case)
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], request_id=request_id, action="approve_qr",
        review_id=settlement["settlement_id"],
        explicit_approval=True, reply_to=str(ctx.agent.address), trace=carry()))


async def step_reimburse(ctx: Context, case: dict, text: str) -> None:
    if case.get("stage") == "organizing":
        await reply(ctx, case, "I’m still organizing the current document. Wait for that review to finish before requesting reimbursement.")
        return
    if case.get("settlement_paused"):
        await reply(ctx, case, "Reimbursement review is paused because a safety check is unresolved. No reimbursement was started.")
        return
    if not case.get("after_care") or case["after_care"].get("payment_status") != "paid":
        await reply(ctx, case, "Please attach and organize a paid receipt before requesting reimbursement.")
        return
    if not case.get("benefits"):
        await reply(ctx, case, "Name the benefit you actually have—for example, an HSA, FSA, HRA, or out-of-network PPO—so I can review that specific path.")
        return
    amount_match = re.search(r"\$?([0-9]+(?:\.[0-9]{1,2})?)", text.replace(",", ""))
    if not amount_match:
        await reply(ctx, case, "Include the externally approved amount. Example: ‘approve reimbursement $120 demo.’")
        return
    demo_approval = MODE == "demo" and "demo" in text.lower()
    if not demo_approval:
        await reply(ctx, case, "Verified administrator approval is still required. For the demo, send: ‘approve reimbursement $120 demo.’")
        return
    benefit = case["benefits"][0]["name"]
    request_id = uuid4().hex
    await core_post("/operations/start", {
        "case_id": case["id"], "kind": "settlement", "request_id": request_id,
    })
    _supersede_pending_operations(case)
    case["pending_settlement_id"] = request_id
    case["pending_settlement_action"] = "reimburse"
    case["pending_settlement_generation"] = _current_turn_arrival(case["id"])
    case["pending_settlement_started_at"] = time.time()
    target_var = globals().get("_REPLY_TARGET")
    current_target = target_var.get() if target_var is not None else None
    if current_target:
        case["pending_settlement_target"] = list(current_target)
    save(ctx, case)
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], request_id=request_id, action="reimburse", benefit_name=benefit,
        amount=float(amount_match.group(1)), benefit_approved=True, explicit_approval=True,
        reply_to=str(ctx.agent.address), trace=carry()))


def _supersede_pending_operations(case: dict) -> list[tuple[str, str]]:
    """Invalidate asynchronous work that no longer belongs to the active request.

    The worker can still finish safely, but its correlation id will no longer
    match and the Coordinator will not replace a newer response with stale
    document or settlement content.
    """
    pending = [
        (kind, request_id)
        for kind, request_id in (
            ("after_care", str(case.get("pending_after_care_id") or "")),
            ("settlement", str(case.get("pending_settlement_id") or "")),
        )
        if request_id
    ]
    for key in (
        "pending_after_care_id", "pending_after_care_generation", "pending_after_care_target",
        "pending_after_care_started_at",
        "pending_settlement_id", "pending_settlement_action", "pending_settlement_target",
        "pending_settlement_generation", "pending_settlement_started_at",
    ):
        case.pop(key, None)
    return pending


async def _cancel_superseded_operations(case_id: str, pending: list[tuple[str, str]]) -> None:
    """Revoke Core mutation grants without delaying the patient on failure."""
    for kind, request_id in pending:
        try:
            await core_post("/operations/cancel", {
                "case_id": case_id, "kind": kind, "request_id": request_id,
            })
        except Exception:
            # Never attach case or operation identifiers to telemetry.
            sentry_sdk.capture_message("background operation cancellation failed", level="warning")


def _after_care_replay(case_id: str, request_id: str, result: dict) -> AfterCareResult:
    """Build a worker-shaped result from Core's deliberately minimal cache."""
    needs_review_value = result.get("needs_review")
    needs_review = (
        sorted({int(value) for value in needs_review_value if str(value).isdigit()})
        if isinstance(needs_review_value, list) else []
    )
    unreviewed_value = result.get("unreviewed_lines", result.get("unreviewed_line_count", 0))
    if isinstance(unreviewed_value, list):
        unreviewed_lines = len({int(value) for value in unreviewed_value if str(value).isdigit()})
    else:
        try:
            unreviewed_lines = max(0, int(unreviewed_value or 0))
        except (TypeError, ValueError):
            unreviewed_lines = 0
    next_steps_value = result.get("next_steps")
    next_steps = (
        [str(value) for value in next_steps_value if isinstance(value, str)]
        if isinstance(next_steps_value, list) else []
    )
    return AfterCareResult(
        case_id=case_id, request_id=request_id, ok=True, lines=[],
        total=float(result.get("total") or 0),
        hospital_npi=str(result.get("hospital_npi") or ""),
        payment_status=str(result.get("payment_status") or "unknown"),
        provider_match=bool(result.get("provider_match")),
        estimate_amount=result.get("estimate_amount"),
        estimate_difference=result.get("estimate_difference"),
        visit_items_matched=int(result.get("visit_items_matched") or 0),
        next_steps=next_steps,
        reader=str(result.get("reader") or "unknown"),
        unreviewed_lines=unreviewed_lines,
        needs_review=needs_review,
        fallback_reason=str(result.get("fallback_reason") or "")[:160],
        trace=carry(),
    )


def _settlement_replay(case_id: str, request_id: str, action: str,
                       result: dict) -> SettlementResult:
    reasons_value = result.get("reasons")
    reasons = (
        [str(value) for value in reasons_value if isinstance(value, str)]
        if isinstance(reasons_value, list) else []
    )
    return SettlementResult(
        case_id=case_id, request_id=request_id, action=action, ok=True,
        status=str(result.get("status") or ""),
        settlement_id=str(result.get("settlement_id") or ""),
        trusted=bool(result.get("trusted")), reasons=reasons,
        merchant_name=str(result.get("merchant_name") or ""),
        amount=float(result.get("amount") or 0),
        handoff_url=str(result.get("handoff_url") or ""),
        mode=str(result.get("mode") or ""), trace=carry(),
    )


async def _reconcile_timed_out_operations(ctx: Context, case: dict,
                                          *, now: float | None = None,
                                          deliver: bool = True) -> bool:
    """Recover a lost worker result without guessing whether Core committed it.

    Callers hold the per-case operation lock. Core is the source of truth: a
    completed mutation is replayed, an active one is left alone, and only an
    inactive exact request is cleared locally.
    """
    now = time.time() if now is None else now
    changed = False
    specs = (
        ("after_care", "pending_after_care_id", "pending_after_care_generation",
         "pending_after_care_started_at", "pending_after_care_target"),
        ("settlement", "pending_settlement_id", "pending_settlement_generation",
         "pending_settlement_started_at", "pending_settlement_target"),
    )
    for kind, id_key, generation_key, started_key, target_key in specs:
        current = load(ctx, case["id"]) or case
        request_id = str(current.get(id_key) or "")
        if not request_id:
            continue
        try:
            started_at = float(current.get(started_key) or 0)
        except (TypeError, ValueError):
            started_at = 0
        if started_at > 0 and now - started_at < OPERATION_TIMEOUT_SECONDS:
            continue
        try:
            status = await core_post("/operations/status", {
                "case_id": current["id"], "kind": kind, "request_id": request_id,
            })
        except Exception:
            # A network failure is not proof that a mutation failed. Preserve
            # the exact correlation id so the next turn can safely retry.
            sentry_sdk.capture_message("operation reconciliation unavailable", level="warning")
            continue
        state = str(status.get("status") or "inactive")
        if state == "active":
            continue
        if state == "completed":
            result = status.get("result")
            action = str(status.get("action") or "")
            if not isinstance(result, dict):
                sentry_sdk.capture_message("operation replay result was invalid", level="warning")
                continue
            result_task = asyncio.current_task()
            if result_task is not None:
                _ACTIVE_RESULT_TURNS[current["id"]] = result_task
            try:
                try:
                    if kind == "after_care" and action == "after_care":
                        await _apply_after_care_result(
                            ctx, _after_care_replay(current["id"], request_id, result),
                            notify=deliver,
                        )
                    elif kind == "settlement" and action in {"inspect_qr", "approve_qr", "reimburse"}:
                        pending_action = str(current.get("pending_settlement_action") or "")
                        if pending_action and pending_action != action:
                            sentry_sdk.capture_message("operation replay action did not match", level="warning")
                            continue
                        await _apply_settlement_result(
                            ctx, _settlement_replay(current["id"], request_id, action, result),
                            notify=deliver,
                        )
                    else:
                        sentry_sdk.capture_message("operation replay action was invalid", level="warning")
                        continue
                except (TypeError, ValueError):
                    sentry_sdk.capture_message("operation replay payload was invalid", level="warning")
                    continue
            finally:
                _COMMITTED_RESULT_TURNS.discard(current["id"])
                if (
                    result_task is not None
                    and _ACTIVE_RESULT_TURNS.get(current["id"]) is result_task
                ):
                    _ACTIVE_RESULT_TURNS.pop(current["id"], None)
            changed = True
            continue

        # Inactive means Core cannot admit another write under this identifier.
        # A conditional cancel is harmless and closes any edge at the TTL bound.
        try:
            await core_post("/operations/cancel", {
                "case_id": current["id"], "kind": kind, "request_id": request_id,
            })
        except Exception:
            sentry_sdk.capture_message("expired operation cleanup failed", level="warning")
        latest = load(ctx, current["id"]) or current
        if str(latest.get(id_key) or "") != request_id:
            continue
        target = latest.pop(target_key, None)
        latest.pop(id_key, None)
        latest.pop(generation_key, None)
        latest.pop(started_key, None)
        if kind == "settlement":
            latest.pop("pending_settlement_action", None)
            message = (
                "The secure settlement review window expired before I received a verified result. "
                "No payment or reimbursement was approved. Please restart that step if you still want to continue."
            )
        else:
            if latest.get("stage") == "organizing":
                latest["stage"] = latest.pop(
                    "stage_before_organizing",
                    "organized" if latest.get("after_care") else "new",
                )
            message = (
                "The secure document-review window expired before I received a verified result. "
                "Any earlier organized record is unchanged. Please re-upload one clear image or PDF to try again."
            )
        save(ctx, latest)
        if deliver:
            await reply(ctx, latest, message, target=target)
        changed = True
    return changed


async def route_text(ctx: Context, case: dict, text: str, files: list[str], is_group: bool = False,
                     attachment_error: str = "") -> None:
    text = normalize_request(text)
    low = text.lower().strip()
    # Emergency wording takes precedence even in upload captions or benefit/payment requests.
    emergency_rule = first_matching_rule(text, SAFETY_RULES)
    if emergency_rule:
        pending: list[tuple[str, str]] = []
        if not is_group:
            pending = _supersede_pending_operations(case)
            case.pop("stage_before_organizing", None)
            case["stage"] = "emergency"
            case["settlement_paused"] = True
            save(ctx, case)
        cancel_task = (
            asyncio.create_task(_cancel_superseded_operations(case["id"], pending))
            if pending else None
        )
        try:
            if cancel_task is not None:
                # Let revocation reach Core before starting an outbound safety reply.
                await asyncio.sleep(0)
            await reply(ctx, case, emergency_rule["say"], group_safe=is_group)
        finally:
            if cancel_task is not None:
                await asyncio.shield(cancel_task)
        return
    if is_group:
        # Group handling is deliberately stateless. In particular, never use
        # an existing group's stage, options, document, settlement, or link.
        immediate = quick_reply(text, has_files=bool(files), stage="new", asked=False)
        if _general_group_explanation(text, immediate):
            await reply(ctx, case, immediate, group_safe=True)
        elif _group_private_action(text, files, attachment_error):
            await reply(ctx, case, GROUP_PRIVATE_REPLY, group_safe=True)
        elif care_request(text) or location_hint(text):
            await step_group_guidance(ctx, case, text)
        elif immediate and immediate.startswith("You’re welcome"):
            await reply(ctx, case, "You’re welcome. I can help with general healthcare-cost or safety questions here.", group_safe=True)
        elif immediate and immediate.startswith("Take care"):
            await reply(ctx, case, "Take care. Start a one-to-one Billo chat whenever you need help with a personal case.", group_safe=True)
        else:
            await reply(ctx, case, GROUP_WELCOME, group_safe=True)
        return
    if attachment_error:
        if attachment_error in {"multiple", "multiple_documents"}:
            message = "Please send one bill or receipt at a time so I can review the correct document."
        else:
            message = "I couldn’t open that attachment for document review."
        await reply(ctx, case, (
            message + " Re-upload one clear JPEG, PNG, WebP, HEIC/HEIF image or PDF under 10 MB. "
            "No charges were invented and no payment was approved.\n"
            "Bill and receipt screen (public demo): https://www.getbillo.us/tools/scan"
        ))
        return
    m = re.fullmatch(r"(?:book|pick|choose|save)(?:\s+(?:option|number|provider))?\s*#?\s*(\d+)(?:\s+(?:please|as my care plan))?", low)
    handoff_candidate = re.sub(r"[.!?]+$", "", low).strip()
    handoff_candidate = re.sub(r"[\s,]+please$", "", handoff_candidate).strip()
    handoff_candidate = re.sub(
        r"^(?:(?:can|could|would)\s+(?:you|i)\s+|i(?:'d| would)?\s+(?:like|want)\s+(?:to\s+)?)",
        "", handoff_candidate,
    ).strip()
    handoff_candidate = re.sub(r"^please\s+", "", handoff_candidate).strip()
    whatsapp_handoff = not files and bool(re.fullmatch(
        r"(?:(?:create|make|send(?:\s+me)?|give me|get)\s+)?(?:a\s+)?"
        r"(?:(?:new|another|fresh)\s+)?whatsapp\s+(?:link|handoff)|"
        r"(?:continue|move|switch)(?:\s+this(?:\s+case)?)?\s+"
        r"(?:in|on|to)\s+whatsapp",
        handoff_candidate,
    ))
    immediate = quick_reply(text, has_files=bool(files), stage=case["stage"], asked=case.get("asked", False))
    if low == "stop":
        pending = _supersede_pending_operations(case)
        if case.get("stage") == "organizing":
            case["stage"] = case.pop(
                "stage_before_organizing", "organized" if case.get("after_care") else "new"
            )
        case["stopped"] = True
        case["settlement_paused"] = True
        case["followup_due"] = 0
        save(ctx, case)
        cancel_task = (
            asyncio.create_task(_cancel_superseded_operations(case["id"], pending))
            if pending else None
        )
        try:
            if cancel_task is not None:
                await asyncio.sleep(0)
            await reply(
                ctx,
                case,
                "Stopped. I canceled queued reminders for this case. Send a new message whenever you want to continue.",
                photon_text="✅ Stopped. Reminders canceled.\nSend a new request whenever you want to continue.",
            )
        finally:
            if cancel_task is not None:
                await asyncio.shield(cancel_task)
    elif whatsapp_handoff and case["stage"] in {"booked", "during", "organized", "settled"}:
        await step_whatsapp_handoff(ctx, case)
    elif whatsapp_handoff and case["stage"] == "organizing":
        await reply(
            ctx, case,
            "I’m still organizing the document. Ask for a new WhatsApp link after the review finishes.",
        )
    elif whatsapp_handoff:
        await reply(
            ctx, case,
            "Save a care plan or organize a bill first. Then ask for a new WhatsApp link to continue that case.",
        )
    elif immediate is not None:
        await reply(ctx, case, immediate)
    elif m and not case["places"]:
        await reply(ctx, case, "There are no current care options to select. Describe the care you need and include your city or ZIP code first.")
    elif m and case["places"]:
        if case.pop("stopped", False):
            save(ctx, case)
        await step_book(ctx, case, int(m.group(1)))
    elif low.startswith("approve clinic payment"):
        await step_approve_clinic_payment(ctx, case)
    elif low.startswith("approve reimbursement"):
        await step_reimburse(ctx, case, text)
    elif any(word in low for word in QR_WORDS):
        await step_scan_clinic_qr(ctx, case, files[0] if files else "", demo="demo" in low)
    elif files or (any(w in low for w in BILL_WORDS) and re.search(r"\bdemo\b", low)):
        payment_status = document_payment_status(text)
        await step_after_care(ctx, case, files[0] if files else "", payment_status,
                              demo=not files and bool(re.search(r"\bdemo\b", low)))
    elif any(w in low for w in BILL_WORDS) and ("photo" in low or "here" in low):
        await reply(ctx, case, "I don’t see an attached document yet. Please attach a clear image or PDF and label it paid or unpaid. I won’t invent charges from a missing bill.")
    elif any(w in low for w in ("hsa", "fsa", "hra", "out of network", "out-of-network", "employer benefit", "student benefit", "travel insurance", "accident insurance", "check benefits")):
        await step_benefits(ctx, case, text)
    elif case["stage"] == "booked" and case.get("asked") and low in ("yes", "y", "i went", "yes i went"):
        await reply(ctx, case, "Thanks for confirming. After the visit, send the final bill or paid receipt. I’ll organize it and explain any items that need review.")
    elif case["stage"] == "booked" and case.get("asked") and low in ("no", "n", "not yet"):
        await reply(ctx, case, "Understood. If you’d like another option, tell me the preferred city or ZIP code and any timing constraints.")
    elif case["stage"] in {"booked", "during"} and any(w in low for w in DONE_WORDS):
        await step_visit_log(ctx, case, text)
    elif not care_request(text, has_prior=bool(case.get("care_query"))) and not location_hint(text):
        await reply(ctx, case, SCOPE_REPLY)
    else:
        # This is a new care-search workflow. A late bill or settlement result
        # from the previous workflow must not answer this unrelated request.
        prior_stage = case.get("stage")
        original_case_id = case["id"]
        pending = _supersede_pending_operations(case)
        if prior_stage == "organizing":
            case["stage"] = case.pop(
                "stage_before_organizing", "organized" if case.get("after_care") else "new"
            )
        save(ctx, case)
        if prior_stage in {"organizing", "organized", "settled"} or case.get("after_care"):
            target_var = globals().get("_REPLY_TARGET")
            target = target_var.get() if target_var is not None else None
            channel, who = tuple(target or (case["channel"], case["who"]))
            case = new_case(ctx, channel, who)
        if pending:
            await _cancel_superseded_operations(original_case_id, pending)
        await step_symptoms(ctx, case, text, group_safe=is_group)


# ------------------------------------------------------------------ ASI:One door
chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    text = text_of(msg)
    priority, emergency = _priority_turn(text)
    arrival = _next_turn_sequence()
    door = _key("asi1", sender)
    hinted_case_id = _record_superseding_ingress(
        ctx,
        door,
        arrival,
        text,
        priority=priority,
        has_attachment=any(
            isinstance(content, ResourceContent)
            for content in getattr(msg, "content", [])
        ),
    )
    registered_case_id = hinted_case_id
    if registered_case_id:
        _register_case_turn(
            registered_case_id, arrival, priority=priority, emergency=emergency,
        )
    door_generation = _register_door_turn(
        door, arrival, priority=priority, emergency=emergency,
    )
    # Acknowledge receipt before waiting behind another turn. This prevents
    # ASI:One redelivery while preserving strict processing order below.
    try:
        await ack(ctx, sender, msg)
    except BaseException:
        await _abandon_door_turn(door, arrival)
        if registered_case_id:
            await _abandon_case_turn(registered_case_id, arrival)
        raise
    async with _door_turn(
        door, door_generation, priority=priority, emergency=emergency,
    ) as door_current:
        if not door_current:
            if registered_case_id:
                await _abandon_case_turn(registered_case_id, arrival)
            return
        # Attachment metadata is useful for uploads, but it must never gate an
        # emergency or STOP response.
        if not priority:
            try:
                await advertise_attachments(ctx, sender, msg)
            except BaseException:
                if registered_case_id:
                    await _abandon_case_turn(registered_case_id, arrival)
                raise
        # Resolve the conversation mapping only after acquiring its stable door
        # lock. A preceding "new case" turn can therefore never be overtaken.
        case = get_case(ctx, "asi1", sender)
        _associate_priority_case(hinted_case_id, case["id"], arrival, priority=priority)
        if registered_case_id and registered_case_id != case["id"]:
            await _abandon_case_turn(registered_case_id, arrival)
            registered_case_id = ""
        case_generation = _register_case_turn(
            case["id"], arrival, priority=priority, emergency=emergency,
        )
        registered_case_id = case["id"]
        async with _case_turn(
            case["id"], case_generation, priority=priority, emergency=emergency,
        ) as case_current:
            if not case_current:
                return
            case = _reload_case(ctx, case)
            if not priority:
                if _recover_interrupted_operations(case):
                    save(ctx, case)
                await _reconcile_timed_out_operations(
                    ctx,
                    case,
                    deliver=not _turn_supersedes_recovered_reply(
                        case,
                        text,
                        has_attachment=any(
                            isinstance(content, ResourceContent)
                            for content in getattr(msg, "content", [])
                        ),
                    ),
                )
            case = _reload_case(ctx, case)
            case["last_target"] = ["asi1", sender]
            save(ctx, case)
            target_var = globals().get("_REPLY_TARGET")
            target_token = target_var.set(("asi1", sender)) if target_var is not None else None
            arrival_var = globals().get("_TURN_ARRIVAL")
            arrival_token = arrival_var.set(arrival) if arrival_var is not None else None
            try:
                with case_scope(case["id"], channel="asi1"), \
                        sentry_sdk.start_transaction(op="billo.case", name="asi1 message") as tx:
                    tx.set_data("case", case_hash(case["id"]))
                    tx.set_data("stage.before", case["stage"] if case["stage"] in METRIC_STAGES else "other")
                    try:
                        # Do not delay an emergency response while downloading an attachment.
                        if priority:
                            await route_text(ctx, case, text, [])
                            return
                        files = await upload_resources(msg)
                        await route_text(ctx, case, text, files)
                    except AttachmentError as exc:
                        sentry_sdk.set_tag("check", "bill_reader")
                        sentry_sdk.capture_message("ASI attachment could not be imported", level="warning")
                        await route_text(ctx, case, text, [], attachment_error=str(exc))
                    except Exception as exc:  # never leave the patient without an answer
                        sentry_sdk.capture_exception(exc)
                        tx.set_status("internal_error")
                        await say(ctx, sender, "I couldn’t complete that request. No care option, document, or payment record was changed. Please try again in a moment.")
            finally:
                if arrival_var is not None and arrival_token is not None:
                    arrival_var.reset(arrival_token)
                if target_var is not None and target_token is not None:
                    target_var.reset(target_token)


@chat.on_message(ChatAcknowledgement)
async def on_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)


# ------------------------------------------------------------------ iMessage door (via gateway)
@agent.on_message(model=InboundText)
async def on_imessage(ctx: Context, sender: str, msg: InboundText):
    if sender != ADDR["gateway"]:
        return
    channel = getattr(msg, "channel", "imessage") or "imessage"
    if channel not in {"imessage", "sms", "whatsapp_business"}:
        return
    handoff_claimed = bool(getattr(msg, "handoff_claimed", False))
    is_group = bool(getattr(msg, "is_group", False))
    priority, emergency = _priority_turn(msg.text)
    arrival = _next_turn_sequence()
    door = _key(channel, msg.space_id)
    if not is_group:
        hinted_case_id = _record_superseding_ingress(
            ctx,
            door,
            arrival,
            msg.text,
            priority=priority,
            explicit_case_id=str(getattr(msg, "case_id", "") or ""),
            has_attachment=bool(getattr(msg, "attachment_url", "")),
            attachment_error=str(getattr(msg, "attachment_error", "") or ""),
        )
    else:
        hinted_case_id = ""
    registered_case_id = hinted_case_id
    if registered_case_id:
        _register_case_turn(
            registered_case_id, arrival, priority=priority, emergency=emergency,
        )
    door_generation = _register_door_turn(
        door, arrival, priority=priority, emergency=emergency,
    )
    async with _door_turn(
        door, door_generation, priority=priority, emergency=emergency,
    ) as door_current:
        if not door_current:
            if registered_case_id:
                await _abandon_case_turn(registered_case_id, arrival)
            return
        if is_group:
            # Never resolve a bearer handoff or load a personal case for a group.
            # The marker also prevents an older saved case from sending a delayed
            # result or reminder back to this now-known group destination.
            ctx.storage.set(_group_target_key(channel, msg.space_id), True)
            await _on_imessage_turn(
                ctx, msg, _group_context(channel, msg.space_id), channel, handoff_claimed, True,
            )
            return
        if msg.case_id:
            # A one-time handoff connects another channel to the same case. Keep
            # the original destination; replies remain request-scoped.
            case = load(ctx, msg.case_id) or get_case(ctx, channel, msg.space_id)
            ctx.storage.set(_key(channel, msg.space_id), case["id"])
        else:
            case = get_case(ctx, channel, msg.space_id)
        _associate_priority_case(hinted_case_id, case["id"], arrival, priority=priority)
        if registered_case_id and registered_case_id != case["id"]:
            await _abandon_case_turn(registered_case_id, arrival)
            registered_case_id = ""
        case_generation = _register_case_turn(
            case["id"], arrival, priority=priority, emergency=emergency,
        )
        registered_case_id = case["id"]
        async with _case_turn(
            case["id"], case_generation, priority=priority, emergency=emergency,
        ) as case_current:
            if not case_current:
                return
            case = _reload_case(ctx, case)
            if not priority:
                if _recover_interrupted_operations(case):
                    save(ctx, case)
                await _reconcile_timed_out_operations(
                    ctx,
                    case,
                    deliver=not _turn_supersedes_recovered_reply(
                        case,
                        msg.text,
                        has_attachment=bool(getattr(msg, "attachment_url", "")),
                        attachment_error=str(getattr(msg, "attachment_error", "") or ""),
                    ),
                )
            case = _reload_case(ctx, case)
            arrival_var = globals().get("_TURN_ARRIVAL")
            arrival_token = arrival_var.set(arrival) if arrival_var is not None else None
            try:
                await _on_imessage_turn(ctx, msg, case, channel, handoff_claimed, False)
            finally:
                if arrival_var is not None and arrival_token is not None:
                    arrival_var.reset(arrival_token)


async def _on_imessage_turn(ctx: Context, msg: InboundText, case: dict, channel: str,
                            handoff_claimed: bool, is_group: bool) -> None:
    if not is_group:
        case = _reload_case(ctx, case)
    if not is_group:
        case["last_target"] = [channel, msg.space_id]
        destinations = case.get("destinations") or {}
        destinations[channel] = msg.space_id
        case["destinations"] = destinations
        save(ctx, case)
    files = [msg.attachment_url] if msg.attachment_url else []
    target_var = globals().get("_REPLY_TARGET")
    target_token = target_var.set((channel, msg.space_id)) if target_var is not None else None
    group_var = globals().get("_GROUP_REPLY")
    group_token = group_var.set(is_group) if group_var is not None else None
    try:
        if not msg.text.strip() and not files and not msg.attachment_error and not handoff_claimed:
            return
        # Continue the trace the Photon bridge started, so Photon -> bridge -> agents is one trace.
        with case_scope(case["id"], channel=channel):
            tx = sentry_sdk.continue_trace(msg.trace or {}, op="billo.case", name=f"{channel} message")
            with sentry_sdk.start_transaction(tx):
                tx.set_data("group", is_group)
                tx.set_data("has_file", bool(files))
                try:
                    if handoff_claimed:
                        if is_group:
                            await reply(ctx, case, GROUP_PRIVATE_REPLY, group_safe=True)
                            return
                        label = "WhatsApp" if channel == "whatsapp_business" else "this chat"
                        await reply(
                            ctx, case,
                            f"Connected. {label} is now linked to your existing Billo care plan. "
                            "You can continue the same visit here without sending the link code again.",
                            photon_text=(
                                f"✅ {label} connected\n\n"
                                "Your existing Billo care plan is ready here.\n"
                                "Continue by sending the service received or attaching the final bill."
                            ),
                        )
                        return
                    await route_text(ctx, case, msg.text, files, is_group=is_group,
                                     attachment_error=msg.attachment_error)
                except Exception as exc:
                    sentry_sdk.capture_exception(exc)
                    tx.set_status("internal_error")
                    await reply(ctx, case, "I couldn’t complete that request. No care option, document, or payment record was changed. Please try again in a moment.")
    finally:
        if group_var is not None and group_token is not None:
            group_var.reset(group_token)
        if target_var is not None and target_token is not None:
            target_var.reset(target_token)


# ------------------------------------------------------------------ after-care result
@agent.on_message(model=AfterCareResult)
async def on_result(ctx: Context, sender: str, res: AfterCareResult):
    if sender != ADDR["bill_auditor"]:
        return
    arrival = _next_turn_sequence()
    generation = _register_case_turn(res.case_id, arrival)
    async with _case_turn(res.case_id, generation) as current:
        if current:
            case = load(ctx, res.case_id)
            pending_generation = int((case or {}).get("pending_after_care_generation") or 0)
            notify = _CASE_SUPERSEDING_USER_ARRIVALS.get(res.case_id, 0) <= pending_generation
            task = asyncio.current_task()
            if task is not None:
                _ACTIVE_RESULT_TURNS[res.case_id] = task
            try:
                await _apply_after_care_result(ctx, res, notify=notify)
            finally:
                _COMMITTED_RESULT_TURNS.discard(res.case_id)
                if task is not None and _ACTIVE_RESULT_TURNS.get(res.case_id) is task:
                    _ACTIVE_RESULT_TURNS.pop(res.case_id, None)


async def _apply_after_care_result(ctx: Context, res: AfterCareResult,
                                   *, notify: bool = True) -> None:
    case = load(ctx, res.case_id)
    if not case:
        return
    pending_id = str(case.get("pending_after_care_id") or "")
    if not pending_id or getattr(res, "request_id", "") != pending_id:
        # Ignore late, duplicated, or pre-upgrade results. Core's operation
        # guard also prevents this result from having changed the durable case.
        return
    operation_generation = int(case.get("pending_after_care_generation") or 0)
    case.pop("pending_after_care_id", None)
    case.pop("pending_after_care_generation", None)
    case.pop("pending_after_care_started_at", None)
    reply_target = case.pop("pending_after_care_target", None)
    destination = reply_target or case.get("last_target")
    if destination and _is_group_target(ctx, case, destination):
        case["stage"] = case.pop("stage_before_organizing", "organized" if case.get("after_care") else "new")
        save(ctx, case)
        _COMMITTED_RESULT_TURNS.add(res.case_id)
        if notify:
            await reply(
                ctx, case, GROUP_PRIVATE_REPLY, target=destination, group_safe=True,
                supersession_generation=operation_generation,
            )
        return
    if not res.ok:
        case["stage"] = case.pop("stage_before_organizing", "organized" if case.get("after_care") else "new")
        save(ctx, case)
        _COMMITTED_RESULT_TURNS.add(res.case_id)
        if notify:
            await reply(ctx, case, (
                "I couldn’t reliably read and organize that document. Any earlier organized record is unchanged. "
                "Please resend a sharper image with all four corners visible, or a readable PDF. "
                "I haven’t invented charges or approved a payment.\n"
                "Bill and receipt screen (public demo): https://www.getbillo.us/tools/scan"
            ), target=reply_target, supersession_generation=operation_generation)
        return
    case.pop("stage_before_organizing", None)
    case["after_care"] = {"total": res.total, "hospital_npi": res.hospital_npi,
                          "payment_status": res.payment_status, "provider_match": res.provider_match,
                          "estimate_amount": res.estimate_amount, "estimate_difference": res.estimate_difference,
                          "reader": res.reader}
    case["stage"] = "organized"
    case_link = await core_post("/case-links", {"case_id": case["id"]})
    visit_url = str(case_link["visit_url"])
    case["case_link_ready"] = True
    save(ctx, case)
    _COMMITTED_RESULT_TURNS.add(res.case_id)
    if not notify:
        return
    kind = "paid receipt" if res.payment_status == "paid" else "unpaid final bill" if res.payment_status == "unpaid" else "document with unconfirmed payment status"
    text = ["Document review complete", f"Type: {kind.title()}", f"Total: ${res.total:,.2f}"]
    if res.reader == "ocr":
        text.append("Reader: local OCR extraction. Review charges against the original document; a printed-total match is not guaranteed.")
    elif res.reader == "vision":
        text.append("Reader: vision-assisted extraction. Review required: compare charges and any unreadable fields with the original document; independent OCR verification may be unavailable.")
    elif res.reader == "demo_fallback":
        text.append("Reader: demo fallback. I could not read the uploaded image reliably; send a clearer photo before relying on this result.")
    if res.unreviewed_lines:
        text.append(f"Review required: {res.unreviewed_lines} charge(s) did not include a readable billing code. Ask the provider for an itemized bill.")
    if res.needs_review:
        nums = ", ".join(str(n) for n in res.needs_review)
        text.append(f"Review required: verify line(s) {nums}; the code and charge could not both be confirmed.")
    text.append("Provider match: confirmed against the saved care plan." if res.provider_match else "Provider match: not confirmed. Review the provider before taking another action.")
    if res.estimate_amount is not None:
        text.append(f"Saved estimate: ${res.estimate_amount:,.2f}\nDifference from document total: ${res.estimate_difference:,.2f}")
    if res.visit_items_matched:
        text.append(f"Visit-log match: {res.visit_items_matched} documented item(s).")
    text.extend(f"- {step}" for step in res.next_steps)
    if res.payment_status == "unpaid":
        text.append("Next step: this record is marked unpaid. Send the clinic’s Visa QR with ‘scan clinic QR’ to verify the merchant and exact amount before any wallet handoff.")
    elif res.payment_status == "unknown":
        text.append("Next step: tell me whether this is a paid receipt or an unpaid bill so I can label the record correctly.")
    text.append("Benefit review: name a benefit you actually have—such as an HSA, FSA, HRA, out-of-network plan, employer, school, travel, or accident benefit. Results are possible paths, not eligibility decisions.")
    await reply(
        ctx,
        case,
        "\n".join(text),
        photon_text=photon_organized_bill(
            kind=kind,
            total=res.total,
            reader=res.reader,
            provider_match=res.provider_match,
            estimate_amount=res.estimate_amount,
            estimate_difference=res.estimate_difference,
            unreviewed_lines=res.unreviewed_lines,
            needs_review=res.needs_review,
            payment_status=res.payment_status,
            visit_url=visit_url,
        ),
        target=reply_target,
        private_visit_url=visit_url,
        supersession_generation=operation_generation,
    )


@agent.on_message(model=SettlementResult)
async def on_settlement(ctx: Context, sender: str, res: SettlementResult):
    if sender != ADDR["payment_guard"]:
        return
    arrival = _next_turn_sequence()
    generation = _register_case_turn(res.case_id, arrival)
    async with _case_turn(res.case_id, generation) as current:
        if current:
            case = load(ctx, res.case_id)
            pending_generation = int((case or {}).get("pending_settlement_generation") or 0)
            notify = _CASE_SUPERSEDING_USER_ARRIVALS.get(res.case_id, 0) <= pending_generation
            task = asyncio.current_task()
            if task is not None:
                _ACTIVE_RESULT_TURNS[res.case_id] = task
            try:
                await _apply_settlement_result(ctx, res, notify=notify)
            finally:
                _COMMITTED_RESULT_TURNS.discard(res.case_id)
                if task is not None and _ACTIVE_RESULT_TURNS.get(res.case_id) is task:
                    _ACTIVE_RESULT_TURNS.pop(res.case_id, None)


async def _apply_settlement_result(ctx: Context, res: SettlementResult,
                                   *, notify: bool = True) -> None:
    case = load(ctx, res.case_id)
    if not case:
        return
    pending_id = str(case.get("pending_settlement_id") or "")
    if not pending_id or getattr(res, "request_id", "") != pending_id:
        return
    pending_action = str(case.get("pending_settlement_action") or "")
    if pending_action and res.action != pending_action:
        return
    operation_generation = int(case.get("pending_settlement_generation") or 0)
    case.pop("pending_settlement_id", None)
    case.pop("pending_settlement_action", None)
    case.pop("pending_settlement_generation", None)
    case.pop("pending_settlement_started_at", None)
    reply_target = case.pop("pending_settlement_target", None)
    destination = reply_target or case.get("last_target")
    if destination and _is_group_target(ctx, case, destination):
        save(ctx, case)
        _COMMITTED_RESULT_TURNS.add(res.case_id)
        if notify:
            await reply(
                ctx, case, GROUP_PRIVATE_REPLY, target=destination, group_safe=True,
                supersession_generation=operation_generation,
            )
        return
    if not res.ok:
        save(ctx, case)
        _COMMITTED_RESULT_TURNS.add(res.case_id)
        if notify:
            await reply(
                ctx, case, f"Settlement stopped. Reason: {res.error}. No money moved.",
                target=reply_target, supersession_generation=operation_generation,
            )
        return
    settlement = dump(res)
    # The wallet handoff is a bearer URL. It belongs only in this immediate
    # response and must not survive in Coordinator storage.
    for key in ("handoff_url", "case_id", "request_id", "trace"):
        settlement.pop(key, None)
    case["settlement"] = settlement
    save(ctx, case)
    _COMMITTED_RESULT_TURNS.add(res.case_id)
    if not notify:
        return
    if res.action == "inspect_qr":
        if not res.trusted:
            await reply(
                ctx, case, "QR verification failed. " + "; ".join(res.reasons) + ". No money moved.",
                target=reply_target, supersession_generation=operation_generation,
            )
        else:
            await reply(ctx, case, (
                "QR verification complete\n"
                f"Merchant: {res.merchant_name}\n"
                f"Amount: ${res.amount:,.2f}\n"
                "Status: verified; no money moved.\n"
                "Next step: reply ‘approve clinic payment’ to open the simulated Visa wallet handoff."
            ), photon_text=(
                f"✅ QR verified\n{res.merchant_name} · ${res.amount:,.2f}\n"
                "No money moved.\nNext · @Billo approve clinic payment"
            ), target=reply_target, supersession_generation=operation_generation)
    elif res.action == "approve_qr":
        await reply(ctx, case, (
            "Visa wallet simulation ready\n"
            f"Handoff: {res.handoff_url}\n"
            f"Mode: {res.mode}\n"
            "No card data was collected and no money moved."
        ), photon_text=(
            f"💳 Visa demo ready\n{res.handoff_url}\n"
            "No card data collected. No money moved."
        ), target=reply_target, supersession_generation=operation_generation)
    elif res.action == "reimburse":
        await reply(ctx, case, (
            "Reimbursement simulation recorded\n"
            f"Amount: ${res.amount:,.2f}\n"
            f"Status: {res.status}\n"
            f"Reference: {res.settlement_id}\n"
            f"Mode: {res.mode}. No real funds moved."
        ), photon_text=(
            f"✅ Reimbursement demo routed · ${res.amount:,.2f}\n"
            f"Status · {res.status}\nRef · {res.settlement_id}\nNo real funds moved."
        ), target=reply_target, supersession_generation=operation_generation)


# ------------------------------------------------------------------ Case Medic
@agent.on_message(model=MedicAction)
async def on_medic(ctx: Context, sender: str, act: MedicAction):
    if sender != ADDR["case_medic"]:
        return
    # Sentry can emit operational alerts without a case tag. Never guess a
    # patient by recency: an absent or unknown keyed case must fail closed.
    if not act.case_id:
        return
    case = load(ctx, act.case_id)
    if not case:
        return
    arrival = _next_turn_sequence()
    generation = _register_case_turn(case["id"], arrival)
    async with _case_turn(case["id"], generation) as current:
        if not current:
            return
        case = load(ctx, case["id"]) or case
        # A diagnostic action may arrive after the patient has stopped or sent
        # an emergency message. Never overwrite that state or send stale copy.
        if case.get("stage") == "emergency" or case.get("stopped"):
            if act.action == "pause_settlement":
                case.setdefault("flags", {})[act.action] = True
                case["settlement_paused"] = True
                save(ctx, case)
            return
        with case_span(act, op="coordinator.heal", name=act.action, case_id=case["id"]):
            await _apply_medic(ctx, case, act)
            metric("count", "billo.medic.applied", action=act.action)


async def _apply_medic(ctx: Context, case: dict, act: MedicAction) -> None:
    case.setdefault("flags", {})[act.action] = True
    if act.action == "pause_settlement":
        case["settlement_paused"] = True
    elif act.action == "reschedule_followup":
        case["asked"] = False
        case["followup_due"] = time.time() + 300
    if act.action == "retry_reader":
        # The original temporary upload may already have been deleted. An empty
        # source would select a synthetic demo, not retry the patient's document.
        if case["stage"] == "organizing":
            case["stage"] = case.pop("stage_before_organizing", "organized" if case.get("after_care") else "new")
        save(ctx, case)
        await reply(ctx, case, (
            "The document could not be reread automatically. Please re-upload one clear bill or receipt image or PDF. "
            "Any earlier organized record is unchanged; no charges were invented and no payment was approved.\n"
            "Bill and receipt screen (public demo): https://www.getbillo.us/tools/scan"
        ))
        return
    save(ctx, case)
    await reply(ctx, case, act.patient_text)


# ------------------------------------------------------------------ "Did you go?" follow-up
async def _run_followup_case(ctx: Context, cid: str, now: float) -> None:
    """Run one reminder behind case FIFO and make it preemptible by ingress."""
    arrival = _next_turn_sequence()
    generation = _register_case_turn(cid, arrival)
    task = asyncio.current_task()
    if task is not None:
        _ACTIVE_FOLLOWUP_TURNS[cid] = task
    try:
        async with _case_turn(cid, generation) as current:
            if not current:
                return
            case = load(ctx, cid)
            if not case:
                return
            if _recover_interrupted_operations(case, now=now):
                save(ctx, case)
            await _reconcile_timed_out_operations(ctx, case, now=now)
            case = load(ctx, cid) or case
            if (
                case["stage"] != "booked" or case.get("stopped")
                or case.get("asked") or not case.get("followup_due")
                or now < case["followup_due"]
            ):
                return
            destination = case.get("last_target") or (case["channel"], case["who"])
            if _is_group_target(ctx, case, destination):
                # A reminder must never surface a private case in a group. Stop
                # the legacy destination; the user can resume in a direct chat.
                case["followup_due"] = 0
                save(ctx, case)
                return
            allowed = await core_get(
                "/reminders/allowed", case_id=cid,
            )  # STOP, quiet hours, 1 per day
            if not allowed.get("ok"):
                return
            # Revalidate after the network wait. Priority ingress cancels this
            # task, and this reload protects against external state updates.
            case = load(ctx, cid) or case
            if (
                case["stage"] != "booked" or case.get("stopped")
                or case.get("asked") or not case.get("followup_due")
            ):
                return
            case["asked"] = True
            save(ctx, case)
            await reply(ctx, case, "Visit follow-up: did you receive care today? Reply yes or no.")
    finally:
        if task is not None and _ACTIVE_FOLLOWUP_TURNS.get(cid) is task:
            _ACTIVE_FOLLOWUP_TURNS.pop(cid, None)


@agent.on_interval(period=60.0)
async def followups(ctx: Context):
    now = time.time()
    with monitor(monitor_slug="visit-followup", monitor_config=FOLLOWUP_MONITOR):
        tasks = [
            asyncio.create_task(_run_followup_case(ctx, cid, now))
            for cid in ctx.storage.get("case_ids") or []
        ]
        if not tasks:
            return
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                sentry_sdk.capture_exception(result)


@agent.on_event("startup")
async def hello(ctx: Context):
    missing = [k for k in ("red_flag", "care_finder", "bill_auditor", "payment_guard") if not ADDR[k]]
    ctx.logger.info(f"Coordinator address: {ctx.agent.address}")
    if missing:
        ctx.logger.warning(f"Set these in .env, then restart: {', '.join('ADDR_' + m.upper() for m in missing)}")


if __name__ == "__main__":
    agent.run()
