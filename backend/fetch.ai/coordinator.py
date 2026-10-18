"""Billo Coordinator: the ONE front door on ASI:One (and, through the gateway, iMessage).

Fetch.ai rule: the complete primary workflow must run inside one ASI:One
conversation, with no custom frontend. This file is that workflow:

  symptoms -> Red-Flag Screener -> Care Finder -> "book 1" (estimate + calendar)
  -> receipt/final bill -> After-Care Organizer -> optional benefits check
  -> guarded clinic QR payment OR approved reimbursement -> next-care planning

It also runs the visit follow-up ("Did you go to your visit today?") on a timer,
watched by Sentry Crons, and applies Case Medic actions.

State lives in ctx.storage (one dict per case). Durable data lives in Tiger Data
through the Core API.
"""
import re
import time
import yaml
from uuid import uuid4

import sentry_sdk
from sentry_sdk.crons import monitor
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec

from common.chat import ack, resources_of, say, text_of
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
from common.screen_links import with_screen_link
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


# ------------------------------------------------------------------ case state
def _key(channel: str, who: str) -> str:
    return f"door:{channel}:{who}"


def get_case(ctx: Context, channel: str, who: str) -> dict:
    case_id = ctx.storage.get(_key(channel, who))
    if case_id and ctx.storage.get(f"case:{case_id}"):
        return ctx.storage.get(f"case:{case_id}")
    case = {"id": uuid4().hex[:12], "channel": channel, "who": who, "stage": "new",
            "places": [], "after_care": None, "benefits": [], "settlement": None,
            "flags": {}, "followup_due": 0, "asked": False}
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


# Stages that are safe to count in Sentry. "emergency" is health data, so it is never a metric.
METRIC_STAGES = {"new", "choosing", "booked", "organizing", "organized", "settled"}

# Sentry Crons: the follow-up timer must check in every minute or Sentry raises an issue.
FOLLOWUP_MONITOR = {
    "schedule": {"type": "interval", "value": 1, "unit": "minute"},
    "checkin_margin": 2,          # minutes late before "missed"
    "max_runtime": 1,             # minutes before "timed out"
    "failure_issue_threshold": 2,
    "recovery_threshold": 1,
}


def save(ctx: Context, case: dict) -> None:
    if case.get("stage") != case.get("_metric_stage"):
        case["_metric_stage"] = case.get("stage")
        if case.get("stage") in METRIC_STAGES:
            metric("count", "billo.case.stage", stage=case["stage"], channel=case.get("channel", ""))
    ctx.storage.set(f"case:{case['id']}", case)
    ctx.storage.set(f"hash:{case_hash(case['id'])}", case["id"])
    ids = set(ctx.storage.get("case_ids") or [])
    ids.add(case["id"])
    ctx.storage.set("case_ids", sorted(ids))


async def reply(ctx: Context, case: dict, text: str, *, photon_text: str | None = None) -> None:
    """Send detailed copy to ASI:One and compact copy to Photon/iMessage."""
    if case["channel"] == "asi1":
        await say(ctx, case["who"], with_screen_link(text, case.get("stage", "new")))
    elif case["channel"] == "imessage" and ADDR["gateway"]:
        await ctx.send(ADDR["gateway"], OutboundText(
            space_id=case["who"], text=with_screen_link(photon_text or text, case.get("stage", "new")), case_id=case["id"], trace=carry()))


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
    est = await core_post("/estimates", {"case_id": case["id"], "npi": place["npi"], "place": place["name"],
                                         "code": case.get("code", ""), "amount": place["price_typical"]})
    case.update(stage="booked", place=place, gfe=est["amount"], followup_due=time.time() + FOLLOWUP_MINUTES * 60, asked=False)
    save(ctx, case)
    link = await core_post("/link-codes", {"case_id": case["id"]})
    await reply(ctx, case, (
        f"Care plan saved\n"
        f"Provider: {place['name']}\n"
        f"Location: {place['address']}\n"
        f"Estimated price: ${est['amount']:,.0f}\n\n"
        "This is not a confirmed appointment. Contact the provider to verify availability and the final price.\n\n"
        f"Calendar: {est['ics_url']}\n"
        f"Google Calendar: {est['gcal_url']}\n\n"
        "During the visit, tell me which services you receive—for example, ‘they did an X-ray’—and I’ll update the running estimate.\n"
        f"To continue on your phone, scan {link['qr_url']} or text {link['code']} to {link['line'] or 'Billo'} within 15 minutes."
    ), photon_text=photon_booking_saved(place, est["amount"], est["ics_url"]))


async def step_visit_log(ctx: Context, case: dict, text: str) -> None:
    res = await core_post("/visit-events", {"case_id": case["id"], "text": text})
    await reply(ctx, case, res["say"])


async def step_after_care(ctx: Context, case: dict, file_url: str, payment_status: str) -> None:
    case["stage"] = "organizing"
    save(ctx, case)
    await reply(
        ctx,
        case,
        "Document received. I’m extracting the provider, charges, and payment status, then comparing them with your saved care plan. I’ll flag anything that needs review.",
        photon_text="📸 Got it — reading your bill.\nChecking provider, charges + saved estimate.",
    )
    await ctx.send(ADDR["bill_auditor"], AfterCareRequest(
        case_id=case["id"], file_url=file_url, demo=not file_url,
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
    await reply(ctx, case, "\n".join(lines), photon_text=photon_benefits(result["paths"]))


async def step_scan_clinic_qr(ctx: Context, case: dict, file_url: str, demo: bool = False) -> None:
    if not case.get("after_care") or case["after_care"].get("payment_status") != "unpaid":
        await reply(ctx, case, "Please attach and organize the unpaid final bill first. I must verify the provider and exact amount before reviewing a clinic QR.")
        return
    await reply(
        ctx,
        case,
        "QR received. I’m verifying the checksum, network marker, clinic identity, currency, and exact bill amount. This review does not move money.",
        photon_text="🔎 Checking this clinic QR…\nMerchant · amount · currency\nNo money moves yet.",
    )
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], action="inspect_qr", file_url=file_url, demo=demo,
        reply_to=str(ctx.agent.address), trace=carry()))


async def step_approve_clinic_payment(ctx: Context, case: dict) -> None:
    if case.get("settlement_paused"):
        await reply(ctx, case, "Payment review is paused because a safety check is unresolved. Approval is unavailable, and no money moved.")
        return
    settlement = case.get("settlement") or {}
    if settlement.get("status") != "verified" or not settlement.get("settlement_id"):
        await reply(ctx, case, "Please scan and verify the clinic Visa QR before requesting approval.")
        return
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], action="approve_qr", review_id=settlement["settlement_id"],
        explicit_approval=True, reply_to=str(ctx.agent.address), trace=carry()))


async def step_reimburse(ctx: Context, case: dict, text: str) -> None:
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
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], action="reimburse", benefit_name=benefit,
        amount=float(amount_match.group(1)), benefit_approved=True, explicit_approval=True,
        reply_to=str(ctx.agent.address), trace=carry()))


async def route_text(ctx: Context, case: dict, text: str, files: list[str], is_group: bool = False) -> None:
    text = normalize_request(text)
    low = text.lower().strip()
    # Emergency wording takes precedence even in upload captions or benefit/payment requests.
    emergency_rule = first_matching_rule(text, SAFETY_RULES)
    if emergency_rule:
        case["stage"] = "emergency"
        save(ctx, case)
        await reply(ctx, case, emergency_rule["say"])
        return
    m = re.fullmatch(r"(?:book|pick|choose|save)(?:\s+(?:option|number|provider))?\s*#?\s*(\d+)(?:\s+(?:please|as my care plan))?", low)
    immediate = quick_reply(text, has_files=bool(files), stage=case["stage"], asked=case.get("asked", False))
    if low == "stop":
        case["stopped"] = True
        case["followup_due"] = 0
        save(ctx, case)
        await reply(
            ctx,
            case,
            "Stopped. I canceled queued reminders for this case. Send a new message whenever you want to continue.",
            photon_text="✅ Stopped. Reminders canceled.\nSend a new request whenever you want to continue.",
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
    elif files or (any(w in low for w in BILL_WORDS) and ("demo" in low or "photo" in low or "here" in low)):
        payment_status = document_payment_status(text)
        await step_after_care(ctx, case, files[0] if files else "", payment_status)
    elif any(w in low for w in ("hsa", "fsa", "hra", "out of network", "out-of-network", "employer benefit", "student benefit", "travel insurance", "accident insurance", "check benefits")):
        await step_benefits(ctx, case, text)
    elif case["stage"] == "booked" and case.get("asked") and low in ("yes", "y", "i went", "yes i went"):
        await reply(ctx, case, "Thanks for confirming. After the visit, send the final bill or paid receipt. I’ll organize it and explain any items that need review.")
    elif case["stage"] == "booked" and case.get("asked") and low in ("no", "n", "not yet"):
        await reply(ctx, case, "Understood. If you’d like another option, tell me the preferred city or ZIP code and any timing constraints.")
    elif case["stage"] == "booked" and any(w in low for w in DONE_WORDS):
        await step_visit_log(ctx, case, text)
    elif not care_request(text, has_prior=bool(case.get("care_query"))) and not location_hint(text):
        await reply(ctx, case, SCOPE_REPLY)
    else:
        await step_symptoms(ctx, case, text, group_safe=is_group)


# ------------------------------------------------------------------ ASI:One door
chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ack(ctx, sender, msg)
    case = get_case(ctx, "asi1", sender)
    with case_scope(case["id"], channel="asi1"), \
            sentry_sdk.start_transaction(op="billo.case", name="asi1 message") as tx:
        tx.set_data("case", case_hash(case["id"]))
        tx.set_data("stage.before", case["stage"] if case["stage"] in METRIC_STAGES else "other")
        try:
            await route_text(ctx, case, text_of(msg), resources_of(msg))
        except Exception as exc:  # never leave the patient without an answer
            sentry_sdk.capture_exception(exc)
            tx.set_status("internal_error")
            await say(ctx, sender, "I couldn’t complete that request. No care option, document, or payment record was changed. Please try again in a moment.")


@chat.on_message(ChatAcknowledgement)
async def on_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)


# ------------------------------------------------------------------ iMessage door (via gateway)
@agent.on_message(model=InboundText)
async def on_imessage(ctx: Context, sender: str, msg: InboundText):
    if sender != ADDR["gateway"]:
        return
    if msg.case_id:  # the QR code linked this chat to an existing case: move the case to iMessage
        case = load(ctx, msg.case_id) or get_case(ctx, "imessage", msg.space_id)
        case["channel"], case["who"] = "imessage", msg.space_id
        save(ctx, case)
        ctx.storage.set(_key("imessage", msg.space_id), case["id"])
    else:
        case = get_case(ctx, "imessage", msg.space_id)
    files = [msg.attachment_url] if msg.attachment_url else []
    if not msg.text.strip() and not files:  # e.g. the QR code text: the bridge already said "Linked"
        return
    # Continue the trace the Photon bridge started, so iMessage -> bridge -> agents is one trace.
    with case_scope(case["id"], channel="imessage"):
        tx = sentry_sdk.continue_trace(msg.trace or {}, op="billo.case", name="imessage")
        with sentry_sdk.start_transaction(tx):
            tx.set_data("group", msg.is_group)
            tx.set_data("has_file", bool(files))
            try:
                await route_text(ctx, case, msg.text, files, is_group=msg.is_group)
            except Exception as exc:
                sentry_sdk.capture_exception(exc)
                tx.set_status("internal_error")
                await reply(ctx, case, "I couldn’t complete that request. No care option, document, or payment record was changed. Please try again in a moment.")


# ------------------------------------------------------------------ after-care result
@agent.on_message(model=AfterCareResult)
async def on_result(ctx: Context, sender: str, res: AfterCareResult):
    case = load(ctx, res.case_id)
    if not case:
        return
    case["after_care"] = {"total": res.total, "hospital_npi": res.hospital_npi,
                          "payment_status": res.payment_status, "provider_match": res.provider_match,
                          "estimate_amount": res.estimate_amount, "estimate_difference": res.estimate_difference,
                          "reader": res.reader}
    case["stage"] = "organized"
    save(ctx, case)
    kind = "paid receipt" if res.payment_status == "paid" else "unpaid final bill" if res.payment_status == "unpaid" else "document with unconfirmed payment status"
    text = ["Document review complete", f"Type: {kind.title()}", f"Total: ${res.total:,.2f}"]
    if res.reader == "ocr":
        text.append("Reader: local OCR; extracted charges matched the printed total.")
    elif res.reader == "vision":
        text.append("Reader: vision fallback; extracted values were checked against the image because local OCR confidence was low.")
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
        ),
    )


@agent.on_message(model=SettlementResult)
async def on_settlement(ctx: Context, sender: str, res: SettlementResult):
    if sender != ADDR["payment_guard"]:
        return
    case = load(ctx, res.case_id)
    if not case:
        return
    if not res.ok:
        await reply(ctx, case, f"Settlement stopped. Reason: {res.error}. No money moved.")
        return
    case["settlement"] = dump(res)
    save(ctx, case)
    if res.action == "inspect_qr":
        if not res.trusted:
            await reply(ctx, case, "QR verification failed. " + "; ".join(res.reasons) + ". No money moved.")
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
            ))
    elif res.action == "approve_qr":
        await reply(ctx, case, (
            "Visa wallet simulation ready\n"
            f"Handoff: {res.handoff_url}\n"
            f"Mode: {res.mode}\n"
            "No card data was collected and no money moved."
        ), photon_text=(
            f"💳 Visa demo ready\n{res.handoff_url}\n"
            "No card data collected. No money moved."
        ))
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
        ))


# ------------------------------------------------------------------ Case Medic
def _latest_case(ctx: Context) -> dict | None:
    """Demo fallback: if the alert has no case tag, heal the most recent open case."""
    for cid in reversed(ctx.storage.get("case_ids") or []):
        case = load(ctx, cid)
        if case and case["stage"] != "emergency":
            return case
    return None

@agent.on_message(model=MedicAction)
async def on_medic(ctx: Context, sender: str, act: MedicAction):
    if sender != ADDR["case_medic"]:
        return
    case = load(ctx, act.case_id) or _latest_case(ctx)
    if not case:
        return
    with case_span(act, op="coordinator.heal", name=act.action, case_id=case["id"]):
        await _apply_medic(ctx, case, act)
        metric("count", "billo.medic.applied", action=act.action)


async def _apply_medic(ctx: Context, case: dict, act: MedicAction) -> None:
    case["flags"][act.action] = True
    if act.action == "pause_settlement":
        case["settlement_paused"] = True
    elif act.action == "reschedule_followup":
        case["asked"] = False
        case["followup_due"] = time.time() + 300
    save(ctx, case)
    await reply(ctx, case, act.patient_text)
    if act.action == "retry_reader" and case["stage"] == "organizing":
        await step_after_care(ctx, case, "", (case.get("after_care") or {}).get("payment_status", "unknown"))


# ------------------------------------------------------------------ "Did you go?" follow-up
@agent.on_interval(period=60.0)
async def followups(ctx: Context):
    now = time.time()
    with monitor(monitor_slug="visit-followup", monitor_config=FOLLOWUP_MONITOR):
        for cid in ctx.storage.get("case_ids") or []:
            case = load(ctx, cid)
            if not case or case["stage"] != "booked" or case.get("stopped") or case.get("asked") or not case.get("followup_due"):
                continue
            if now < case["followup_due"]:
                continue
            allowed = await core_get("/reminders/allowed", case_id=cid)  # STOP, quiet hours, 1 per day
            if not allowed.get("ok"):
                continue
            case["asked"] = True
            save(ctx, case)
            await reply(ctx, case, "Visit follow-up: did you receive care today? Reply yes or no.")


@agent.on_event("startup")
async def hello(ctx: Context):
    missing = [k for k in ("red_flag", "care_finder", "bill_auditor", "payment_guard") if not ADDR[k]]
    ctx.logger.info(f"Coordinator address: {ctx.agent.address}")
    if missing:
        ctx.logger.warning(f"Set these in .env, then restart: {', '.join('ADDR_' + m.upper() for m in missing)}")


if __name__ == "__main__":
    agent.run()
