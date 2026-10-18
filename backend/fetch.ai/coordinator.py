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
from uuid import uuid4

import sentry_sdk
from sentry_sdk.crons import monitor
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec

from common.chat import ack, resources_of, say, text_of
from common.config import ADDR, FOLLOWUP_MINUTES, MODE, PORTS, READMES, require_seed
from common.core import core_get, core_post
from common.conversation import normalize_request, payment_status as document_payment_status, quick_reply
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
from common.tracing import carry, case_hash, case_scope, case_span, init_sentry, metric

init_sentry("coordinator")

agent = Agent(
    name="billo-coordinator",
    seed=require_seed("coordinator"),
    port=PORTS["coordinator"],
    mailbox=True,
    publish_agent_details=True,
    handle_messages_concurrently=True,
    readme_path=str(READMES / "coordinator.md"),
    description=(
        "Billo compares real care prices before a visit and organizes bills, receipts, benefits, "
        "reimbursements, and next steps after care with safety first."
    ),
)

BILL_WORDS = ("bill", "invoice", "statement", "receipt", "charged", "owe")
QR_WORDS = ("visa qr", "clinic qr", "scan qr", "scan to pay", "payment qr")
DONE_WORDS = ("they did", "gave me", "x-ray", "xray", "splint", "brace", "shot", "stitches")


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
        await say(ctx, case["who"], text)
    elif case["channel"] == "imessage" and ADDR["gateway"]:
        await ctx.send(ADDR["gateway"], OutboundText(
            space_id=case["who"], text=photon_text or text, case_id=case["id"], trace=carry()))


# ------------------------------------------------------------------ steps
async def step_symptoms(ctx: Context, case: dict, text: str, group_safe: bool = False) -> None:
    res, _ = await ctx.send_and_receive(
        ADDR["red_flag"], ScreenRequest(case_id=case["id"], text=text, trace=carry()),
        response_type=ScreenResult, timeout=20)
    if res is None:
        await reply(ctx, case, "My safety check did not answer. If this could be an emergency, call 911 now.")
        return
    if res.emergency:
        case["stage"] = "emergency"
        save(ctx, case)
        await reply(ctx, case, res.message)
        return
    opts, _ = await ctx.send_and_receive(
        ADDR["care_finder"], FindCareRequest(case_id=case["id"], text=text, group_safe=group_safe, trace=carry()),
        response_type=CareOptions, timeout=30)
    if opts is None:
        await reply(ctx, case, "I could not load places right now. Please try again in a minute.")
        return
    case["places"] = [dump(p) for p in opts.places]
    case["code"] = opts.code
    case["stage"] = "choosing"
    save(ctx, case)
    # TODO(cards): send this as an ASI1 Interactive Card carousel (see AGENTS.md)
    lines = [f"No emergency signs found. Here are {len(opts.places)} places near you, with real prices:"]
    for i, p in enumerate(opts.places, 1):
        lines.append(f"{i}. {p.name} ({p.kind.replace('_', ' ')}) · about ${p.price_typical:,.0f} · {p.hours}")
    lines.append("Reply 'book 1', 'book 2' or 'book 3'.")
    await reply(ctx, case, "\n".join(lines), photon_text=photon_care_matches(case["places"]))


async def step_book(ctx: Context, case: dict, n: int) -> None:
    if not (1 <= n <= len(case["places"])):
        choices = ", ".join(f"{i}. {place['name']}" for i, place in enumerate(case["places"], 1))
        await reply(ctx, case, f"Please choose a valid option: {choices}.")
        return
    place = case["places"][n - 1]
    est = await core_post("/estimates", {"case_id": case["id"], "npi": place["npi"], "place": place["name"],
                                         "code": case.get("code", ""), "amount": place["price_typical"]})
    case.update(stage="booked", place=place, gfe=est["amount"], followup_due=time.time() + FOLLOWUP_MINUTES * 60, asked=False)
    save(ctx, case)
    link = await core_post("/link-codes", {"case_id": case["id"]})
    await reply(ctx, case, (
        f"Booked: {place['name']}, {place['address']}.\n"
        f"Good Faith Estimate saved: ${est['amount']:,.0f}. I will use it to organize your final record after care.\n"
        f"Add to calendar: {est['ics_url']}  (or Google Calendar: {est['gcal_url']})\n"
        f"At the clinic you can tell me what they do (for example 'they did an X-ray') and I keep a running total.\n"
        f"Want this on your iPhone? Scan {link['qr_url']} or text {link['code']} to {link['line'] or 'Billo'} within 15 minutes."
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
        "Reading the document now. I will organize the payment record and match it to your saved care plan.",
        photon_text="📸 Got it — reading your bill.\nChecking provider, charges + saved estimate.",
    )
    await ctx.send(ADDR["bill_auditor"], AfterCareRequest(
        case_id=case["id"], file_url=file_url, demo=not file_url,
        hospital_npi=(case.get("place") or {}).get("npi", ""), payment_status=payment_status,
        reply_to=str(ctx.agent.address), trace=carry()))


async def step_benefits(ctx: Context, case: dict, text: str) -> None:
    if not case.get("after_care"):
        await reply(ctx, case, "Send a receipt or final bill first so I can attach any benefit path to the right visit.")
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
        await reply(ctx, case, "First send and organize the unpaid final bill. I need its verified provider and amount before I can trust a clinic QR.")
        return
    await reply(
        ctx,
        case,
        "Checking the QR checksum, Visa network marker, clinic identity, currency and exact bill amount. No money moves during this check.",
        photon_text="🔎 Checking this clinic QR…\nMerchant · amount · currency\nNo money moves yet.",
    )
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], action="inspect_qr", file_url=file_url, demo=demo,
        reply_to=str(ctx.agent.address), trace=carry()))


async def step_approve_clinic_payment(ctx: Context, case: dict) -> None:
    if case.get("settlement_paused"):
        await reply(ctx, case, "This settlement is paused for review. I cannot approve it while a safety check is unresolved. No money moved.")
        return
    settlement = case.get("settlement") or {}
    if settlement.get("status") != "verified" or not settlement.get("settlement_id"):
        await reply(ctx, case, "Scan and verify the clinic Visa QR first.")
        return
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], action="approve_qr", review_id=settlement["settlement_id"],
        explicit_approval=True, reply_to=str(ctx.agent.address), trace=carry()))


async def step_reimburse(ctx: Context, case: dict, text: str) -> None:
    if case.get("settlement_paused"):
        await reply(ctx, case, "This settlement is paused for review. I cannot start reimbursement while a safety check is unresolved.")
        return
    if not case.get("after_care") or case["after_care"].get("payment_status") != "paid":
        await reply(ctx, case, "A paid receipt must be organized before reimbursement.")
        return
    if not case.get("benefits"):
        await reply(ctx, case, "Name your real benefit first (for example HSA, FSA, HRA, or out-of-network PPO), so I can check that path.")
        return
    amount_match = re.search(r"\$?([0-9]+(?:\.[0-9]{1,2})?)", text.replace(",", ""))
    if not amount_match:
        await reply(ctx, case, "Include the externally approved amount, for example: approve reimbursement $120 demo.")
        return
    demo_approval = MODE == "demo" and "demo" in text.lower()
    if not demo_approval:
        await reply(ctx, case, "I still need verified approval from the benefit administrator. For the stage demo, say: approve reimbursement $120 demo.")
        return
    benefit = case["benefits"][0]["name"]
    await ctx.send(ADDR["payment_guard"], SettlementRequest(
        case_id=case["id"], action="reimburse", benefit_name=benefit,
        amount=float(amount_match.group(1)), benefit_approved=True, explicit_approval=True,
        reply_to=str(ctx.agent.address), trace=carry()))


async def route_text(ctx: Context, case: dict, text: str, files: list[str], is_group: bool = False) -> None:
    text = normalize_request(text)
    low = text.lower().strip()
    m = re.fullmatch(r"(?:book|pick|choose)\s*#?\s*(\d+)", low)
    immediate = quick_reply(text, has_files=bool(files), stage=case["stage"], asked=case.get("asked", False))
    if low == "stop":
        case["stopped"] = True
        case["followup_due"] = 0
        save(ctx, case)
        await reply(
            ctx,
            case,
            "Stopped. I canceled queued reminders for this case. Send a new message whenever you want to continue.",
            photon_text="✅ Stopped. Reminders canceled.\nTag @Billo whenever you want to restart.",
        )
    elif immediate is not None:
        await reply(ctx, case, immediate)
    elif m and not case["places"]:
        await reply(ctx, case, "Find care first so I can show valid choices. Tell me what care you need and your city or ZIP code.")
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
        await reply(ctx, case, "Great. After care, send the final bill or paid receipt. I will organize it and show the next steps.")
    elif case["stage"] == "booked" and case.get("asked") and low in ("no", "n", "not yet"):
        await reply(ctx, case, "No problem. Do you want me to find another time or place? Tell me what happened.")
    elif case["stage"] == "booked" and any(w in low for w in DONE_WORDS):
        await step_visit_log(ctx, case, text)
    elif low in ("help", "?"):
        await reply(
            ctx,
            case,
            "Tell me what happened, or send a final bill or paid receipt. For an unpaid bill I can verify a clinic Visa QR; for a paid receipt I can route an approved reimbursement. Text STOP to stop messages.",
            photon_text="👋 Your care companion\n\nPay less for care. Explore money-back options.\n\nTry one:\n@Billo find care near [ZIP]\n@Billo check this receipt + photo\n@Billo check my benefits\n\nClinic QR payments are simulated.\nText STOP to stop reminders.",
        )
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
            await say(ctx, sender, "Something went wrong on my side. I am fixing it. Please try again in a minute.")


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
                await reply(ctx, case, "Something went wrong on my side. I am fixing it. Please try again in a minute.")


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
    text = [f"Done. I organized this {kind} for ${res.total:,.2f}."]
    if res.reader == "ocr":
        text.append("I read it locally with OCR, and the parsed charges matched the printed total.")
    elif res.reader == "vision":
        text.append("Local OCR was not confident enough, so I used the vision fallback and checked its numbers against the image.")
    elif res.reader == "demo_fallback":
        text.append("I could not read that image safely, so this result uses the demo document. Please send a clearer photo.")
    if res.unreviewed_lines:
        text.append(f"Ask the hospital about {res.unreviewed_lines} charge(s) that had no readable billing code.")
    if res.needs_review:
        nums = ", ".join(str(n) for n in res.needs_review)
        text.append(f"Please verify line(s) {nums}; OCR could not confirm both the code and charge.")
    text.append("Provider matches the saved care plan." if res.provider_match else "Provider does not match the saved care plan; I marked it for your review.")
    if res.estimate_amount is not None:
        text.append(f"Saved estimate: ${res.estimate_amount:,.2f}; difference: ${res.estimate_difference:,.2f}.")
    if res.visit_items_matched:
        text.append(f"Matched {res.visit_items_matched} documented visit item(s).")
    text.extend(f"- {step}" for step in res.next_steps)
    if res.payment_status == "unpaid":
        text.append("I saved this as an amount due. Send the clinic's Visa QR with 'scan clinic QR' and I will verify the merchant and exact amount before any wallet handoff.")
    elif res.payment_status == "unknown":
        text.append("Tell me whether this is a paid receipt or an unpaid bill so the record is labeled correctly.")
    text.append("If you have an HSA, FSA, HRA, out-of-network plan, employer, school, travel, or accident benefit, tell me which one. I will check possible paths without promising eligibility.")
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
        await reply(ctx, case, f"I stopped the settlement: {res.error}")
        return
    case["settlement"] = dump(res)
    save(ctx, case)
    if res.action == "inspect_qr":
        if not res.trusted:
            await reply(ctx, case, "I rejected this QR. " + "; ".join(res.reasons))
        else:
            await reply(ctx, case, (
                f"Verified: {res.merchant_name}, ${res.amount:,.2f}. No money has moved. "
                "Reply 'approve clinic payment' to open the Visa wallet handoff."
            ), photon_text=(
                f"✅ QR verified\n{res.merchant_name} · ${res.amount:,.2f}\n"
                "No money moved.\nNext · @Billo approve clinic payment"
            ))
    elif res.action == "approve_qr":
        await reply(ctx, case, (
            f"Your verified Visa wallet handoff simulation is ready: {res.handoff_url} "
            f"({res.mode} mode). No card data was collected and no money moved."
        ), photon_text=(
            f"💳 Visa demo ready\n{res.handoff_url}\n"
            "No card data collected. No money moved."
        ))
    elif res.action == "reimburse":
        await reply(ctx, case, (
            f"Reimbursement routed: ${res.amount:,.2f}, status {res.status}, reference {res.settlement_id}. "
            f"This is {res.mode} mode; no real funds moved in the demo."
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
            await reply(ctx, case, "Did you go to your visit today? Reply yes or no.")


@agent.on_event("startup")
async def hello(ctx: Context):
    missing = [k for k in ("red_flag", "care_finder", "bill_auditor", "payment_guard") if not ADDR[k]]
    ctx.logger.info(f"Coordinator address: {ctx.agent.address}")
    if missing:
        ctx.logger.warning(f"Set these in .env, then restart: {', '.join('ADDR_' + m.upper() for m in missing)}")


if __name__ == "__main__":
    agent.run()
