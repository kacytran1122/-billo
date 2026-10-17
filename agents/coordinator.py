"""Billo Coordinator: the ONE front door on ASI:One (and, through the gateway, iMessage).

Fetch.ai rule: the complete primary workflow must run inside one ASI:One
conversation, with no custom frontend. This file is that workflow:

  symptoms -> Red-Flag Screener -> Care Finder -> "book 1" (estimate + calendar)
  -> bill photo -> Bill Auditor (live, line by line) -> "approve"
  -> Payment Guard -> Agent Payment Protocol (RequestPayment) -> paid

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
from uagents_core.contrib.protocols.payment import (
    CancelPayment,
    CommitPayment,
    CompletePayment,
    Funds,
    RejectPayment,
    RequestPayment,
    payment_protocol_spec,
)

from common.chat import ack, resources_of, say, text_of
from common.config import ADDR, FOLLOWUP_MINUTES, PORTS, READMES, require_seed
from common.core import core_get, core_post
from common.models import (
    AuditRequest,
    AuditResult,
    AuditUpdate,
    CareOptions,
    FindCareRequest,
    InboundText,
    MedicAction,
    OutboundText,
    PayDecision,
    PayRequest,
    ScreenRequest,
    ScreenResult,
    dump,
)
from common.tracing import carry, case_hash, init_sentry

init_sentry("coordinator")

agent = Agent(
    name="billo-coordinator",
    seed=require_seed("coordinator"),
    port=PORTS["coordinator"],
    mailbox=True,
    publish_agent_details=True,
    handle_messages_concurrently=True,  # live audit updates must not wait behind a long handler
    readme_path=str(READMES / "coordinator.md"),
    description=(
        "Billo: care without the sticker shock. Finds affordable care near you, checks your medical bill "
        "line by line for mistakes, disputes unfair charges and pays only the fair amount with Visa."
    ),
)

DEFAULT_LIMIT = 500.0  # demo mandate: max the patient lets Billo pay without asking again
BILL_WORDS = ("bill", "invoice", "statement", "charged", "owe")
DONE_WORDS = ("they did", "gave me", "x-ray", "xray", "splint", "brace", "shot", "stitches")


# ------------------------------------------------------------------ case state
def _key(channel: str, who: str) -> str:
    return f"door:{channel}:{who}"


def get_case(ctx: Context, channel: str, who: str) -> dict:
    case_id = ctx.storage.get(_key(channel, who))
    if case_id and ctx.storage.get(f"case:{case_id}"):
        return ctx.storage.get(f"case:{case_id}")
    case = {"id": uuid4().hex[:12], "channel": channel, "who": who, "stage": "new",
            "places": [], "audit": None, "pay": None, "flags": {}, "followup_due": 0, "asked": False}
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


def save(ctx: Context, case: dict) -> None:
    ctx.storage.set(f"case:{case['id']}", case)
    ctx.storage.set(f"hash:{case_hash(case['id'])}", case["id"])
    ids = set(ctx.storage.get("case_ids") or [])
    ids.add(case["id"])
    ctx.storage.set("case_ids", sorted(ids))


async def reply(ctx: Context, case: dict, text: str) -> None:
    """Send to whichever door this case is using now."""
    if case["channel"] == "asi1":
        await say(ctx, case["who"], text)
    elif case["channel"] == "imessage" and ADDR["gateway"]:
        await ctx.send(ADDR["gateway"], OutboundText(space_id=case["who"], text=text, case_id=case["id"]))


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
        if p.picture_url and not group_safe:
            lines.append(f"   Picture: {p.picture_url}")
    lines.append("Booking happens in a private chat." if group_safe else "Reply 'book 1', 'book 2' or 'book 3'.")
    await reply(ctx, case, "\n".join(lines))


async def step_book(ctx: Context, case: dict, n: int) -> None:
    if not (1 <= n <= len(case["places"])):
        await reply(ctx, case, "Please pick one of the numbers in the list.")
        return
    place = case["places"][n - 1]
    est = await core_post("/estimates", {"case_id": case["id"], "npi": place["npi"], "place": place["name"],
                                         "code": case.get("code", ""), "amount": place["price_typical"]})
    case.update(stage="booked", place=place, gfe=est["amount"], followup_due=time.time() + FOLLOWUP_MINUTES * 60, asked=False)
    save(ctx, case)
    link = await core_post("/link-codes", {"case_id": case["id"]})
    await reply(ctx, case, (
        f"Booked: {place['name']}, {place['address']}.\n"
        f"Good Faith Estimate saved: ${est['amount']:,.0f}. If the bill is $400 or more over this, you can dispute it.\n"
        f"Add to calendar: {est['ics_url']}  (or Google Calendar: {est['gcal_url']})\n"
        f"At the clinic you can tell me what they do (for example 'they did an X-ray') and I keep a running total.\n"
        f"Want this on your iPhone? Scan {link['qr_url']} or text {link['code']} to {link['line'] or 'Billo'} within 15 minutes."
    ))


async def step_visit_log(ctx: Context, case: dict, text: str) -> None:
    res = await core_post("/visit-events", {"case_id": case["id"], "text": text})
    await reply(ctx, case, res["say"])


async def step_audit(ctx: Context, case: dict, file_url: str) -> None:
    case["stage"] = "auditing"
    save(ctx, case)
    await reply(ctx, case, "Reading your bill now. I will check it line by line and tell you what I find as I go.")
    await ctx.send(ADDR["bill_auditor"], AuditRequest(
        case_id=case["id"], file_url=file_url, demo=not file_url,
        hospital_npi=(case.get("place") or {}).get("npi", ""), reply_to=str(ctx.agent.address), trace=carry()))


async def step_approve(ctx: Context, case: dict) -> None:
    audit = case.get("audit")
    if not audit:
        await reply(ctx, case, "There is nothing to approve yet. Send me a photo of your bill first.")
        return
    if case["flags"].get("pause_guard"):
        await reply(ctx, case, "Payments are paused on this case for safety. I will tell you when it is safe.")
        return
    dec, _ = await ctx.send_and_receive(ADDR["payment_guard"], PayRequest(
        case_id=case["id"], hospital_npi=audit["hospital_npi"], amount=audit["fair_amount"],
        disputed_amount=audit["disputed_amount"], mandate_max=max(DEFAULT_LIMIT, audit["fair_amount"]), trace=carry()),
        response_type=PayDecision, timeout=30)
    if dec is None or not dec.approved:
        why = "; ".join(dec.reasons) if dec else "the Payment Guard did not answer"
        await reply(ctx, case, f"I did not pay. Reason: {why}.")
        return
    case.update(stage="paying", pay={"payment_id": dec.payment_id, "link": dec.pay_link, "amount": audit["fair_amount"]})
    save(ctx, case)
    letter = await core_post("/disputes/letter", {"case_id": case["id"]})
    await reply(ctx, case, (
        "Verified: " + "; ".join(dec.reasons) + ".\n"
        f"Dispute letter ready: {letter['url']}\n"
        f"Pay only the fair part, ${audit['fair_amount']:,.2f}, here: {dec.pay_link}\n"
        f"The disputed ${audit['disputed_amount']:,.2f} is held back until the hospital answers."
    ))
    if case["channel"] == "asi1":  # Fetch.ai Agent Payment Protocol
        await ctx.send(case["who"], RequestPayment(
            accepted_funds=[Funds(amount=f"{audit['fair_amount']:.2f}", currency="USD", payment_method="visa_pay_link")],
            recipient=str(ctx.agent.address), deadline_seconds=3600, reference=case["id"],
            description="Fair part of your bill (disputed part held back)",
            metadata={"pay_link": dec.pay_link, "payment_id": dec.payment_id}))


async def step_check_paid(ctx: Context, case: dict) -> None:
    status = await core_get(f"/visa/status/{case['pay']['payment_id']}")
    if status.get("paid"):
        case["stage"] = "paid"
        save(ctx, case)
        await reply(ctx, case, "Paid. The fair part is done, and the disputed part is still held back.")
    else:
        await reply(ctx, case, "I do not see the payment yet. Please finish it on the Visa page first.")


async def route_text(ctx: Context, case: dict, text: str, files: list[str], is_group: bool = False) -> None:
    low = text.lower().strip()
    if is_group:  # group chat: before care only, general words, nothing private
        if files or any(w in low for w in BILL_WORDS):
            await reply(ctx, case, "Bills are private. Please send it to me in a private chat.")
            return
        await step_symptoms(ctx, case, text, group_safe=True)
        return
    m = re.match(r"^(book|pick|choose)\s*#?\s*(\d)", low)
    if m and case["places"]:
        await step_book(ctx, case, int(m.group(2)))
    elif files or (any(w in low for w in BILL_WORDS) and ("demo" in low or "photo" in low or "here" in low)):
        await step_audit(ctx, case, files[0] if files else "")
    elif low in ("approve", "approve dispute", "yes approve", "pay") or low.startswith("approve"):
        await step_approve(ctx, case)
    elif low in ("paid", "i paid", "done") and case.get("pay"):
        await step_check_paid(ctx, case)
    elif case["stage"] == "booked" and case.get("asked") and low in ("yes", "y", "i went", "yes i went"):
        await reply(ctx, case, "Great. When your bill comes, send me a photo and I will check it.")
    elif case["stage"] == "booked" and case.get("asked") and low in ("no", "n", "not yet"):
        await reply(ctx, case, "No problem. Do you want me to find another time or place? Tell me what happened.")
    elif case["stage"] == "booked" and any(w in low for w in DONE_WORDS):
        await step_visit_log(ctx, case, text)
    elif low in ("help", "?"):
        await reply(ctx, case, "Tell me what happened, or send a photo of a medical bill. Text STOP to stop messages.")
    else:
        await step_symptoms(ctx, case, text)


# ------------------------------------------------------------------ ASI:One door
chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ack(ctx, sender, msg)
    case = get_case(ctx, "asi1", sender)
    sentry_sdk.set_tag("case", case_hash(case["id"]))
    with sentry_sdk.start_transaction(op="billo.case", name="asi1 message"):
        try:
            await route_text(ctx, case, text_of(msg), resources_of(msg))
        except Exception as exc:  # never leave the patient without an answer
            sentry_sdk.capture_exception(exc)
            await say(ctx, sender, "Something went wrong on my side. I am fixing it. Please try again in a minute.")


@chat.on_message(ChatAcknowledgement)
async def on_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)

# ------------------------------------------------------------------ Payment Protocol (seller role)
pay = Protocol(spec=payment_protocol_spec, role="seller")


@pay.on_message(CommitPayment)
async def on_commit(ctx: Context, sender: str, msg: CommitPayment):
    case = load(ctx, msg.reference or "")
    if not case or not case.get("pay"):
        await ctx.send(sender, CancelPayment(transaction_id=msg.transaction_id, reason="unknown case"))
        return
    status = await core_get(f"/visa/status/{case['pay']['payment_id']}")
    if status.get("paid"):
        case["stage"] = "paid"
        save(ctx, case)
        await ctx.send(sender, CompletePayment(transaction_id=msg.transaction_id))
        await reply(ctx, case, "Paid. The fair part is done, and the disputed part is still held back.")
    else:
        await reply(ctx, case, "I do not see the Visa payment yet. Please finish it on the Visa page, then tell me 'paid'.")


@pay.on_message(RejectPayment)
async def on_reject(ctx: Context, sender: str, msg: RejectPayment):
    ctx.logger.info(f"payment rejected by {sender[:12]}: {msg.reason}")


agent.include(pay, publish_manifest=True)


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
    with sentry_sdk.start_transaction(op="billo.case", name="imessage"):
        await route_text(ctx, case, msg.text, files, is_group=msg.is_group)


# ------------------------------------------------------------------ live audit stream
@agent.on_message(model=AuditUpdate)
async def on_update(ctx: Context, sender: str, up: AuditUpdate):
    case = load(ctx, up.case_id)
    if case and up.status != "ok":  # only speak when there is something to say
        await reply(ctx, case, f"Line {up.line_no} of {up.total_lines}: {up.text}  (possible savings so far: ${up.running_total:,.0f})")


@agent.on_message(model=AuditResult)
async def on_result(ctx: Context, sender: str, res: AuditResult):
    case = load(ctx, res.case_id)
    if not case:
        return
    case["audit"] = {"fair_amount": res.fair_amount, "disputed_amount": res.disputed_amount,
                     "hospital_npi": res.hospital_npi, "flags": [dump(f) for f in res.flags]}
    case["stage"] = "audited"
    save(ctx, case)
    disputes = [f for f in res.flags if f.kind == "dispute"]
    asks = [f for f in res.flags if f.kind == "ask_hospital"]
    text = [f"Done. Your bill is ${res.total_billed:,.2f}. I found {len(disputes)} thing(s) to dispute and {len(asks)} to ask about."]
    text += [f"- Dispute: {f.explanation}" for f in disputes]
    text += [f"- Ask the hospital: {f.explanation}" for f in asks]
    if res.charity_care_hint:
        text.append(f"- {res.charity_care_hint}")
    text.append(f"Fair amount: ${res.fair_amount:,.2f}. Reply 'approve' to send the dispute and pay only the fair part.")
    await reply(ctx, case, "\n".join(text))


# ------------------------------------------------------------------ Case Medic
def _latest_case(ctx: Context) -> dict | None:
    """Demo fallback: if the alert has no case tag, heal the most recent open case."""
    for cid in reversed(ctx.storage.get("case_ids") or []):
        case = load(ctx, cid)
        if case and case["stage"] not in ("paid", "emergency"):
            return case
    return None

@agent.on_message(model=MedicAction)
async def on_medic(ctx: Context, sender: str, act: MedicAction):
    if sender != ADDR["case_medic"]:
        return
    case = load(ctx, act.case_id) or _latest_case(ctx)
    if not case:
        return
    case["flags"][act.action] = True
    save(ctx, case)
    await reply(ctx, case, act.patient_text)
    if act.action == "retry_reader" and case["stage"] == "auditing":
        await step_audit(ctx, case, "")


# ------------------------------------------------------------------ "Did you go?" follow-up
@agent.on_interval(period=30.0)
async def followups(ctx: Context):
    now = time.time()
    with monitor(monitor_slug="visit-followup"):
        for cid in ctx.storage.get("case_ids") or []:
            case = load(ctx, cid)
            if not case or case["stage"] != "booked" or case.get("asked") or not case.get("followup_due"):
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
