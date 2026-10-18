"""Case Medic (helper): Sentry inside the product loop.

Sentry alert webhook -> Core API /sentry/webhook -> POST /alert here.
1. Read the trace through the Sentry API (if a token is set).
2. Pick one fixed action (plain rules, no LLM):
   bill_reader -> retry_reader   (stricter schema / backup model)
   npi/delivery -> review_record (keep the record open for human review)
   settlement  -> pause_settlement (never continue a money action after an error)
   followup    -> reschedule_followup (retry the reminder safely later)
3. Tell the Coordinator, which applies it and texts the patient.
4. Record the action as a span on the same trace.
"""
import uuid

import httpx
import sentry_sdk
from uagents import Agent, Context

from common.config import ADDR, INTERNAL_TOKEN, PORTS, READMES, env, require_seed
from common.models import Ack, Alert, MedicAction
from common.tracing import carry, case_scope, init_sentry, metric

init_sentry("case_medic")

ACTIONS = {
    "bill_reader": ("retry_reader", "I am reading your bill again more carefully. One moment."),
    "npi": ("review_record", "I could not confirm the provider right now. I kept your record open and did not guess."),
    "settlement": ("pause_settlement", "I paused this settlement check. Nothing moved and the record is ready for review."),
    "delivery": ("review_record", "A message could not be delivered. I kept your record open without changing it."),
    "followup": ("reschedule_followup", "The follow-up check was delayed. I safely scheduled it to try again."),
    "workflow": ("review_record", "One check needs review. I kept your record open and did not infer a result."),
}
SENTRY_API = env("SENTRY_API_URL", "https://sentry.io").rstrip("/")

agent = Agent(
    name="billo-case-medic",
    seed=require_seed("case_medic"),
    port=PORTS["case_medic"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "case_medic.md"),
    description="Helper that reads Sentry alerts and traces and fixes a Billo case by itself.",
)


async def read_trace(trace_id: str) -> int:
    """How many transactions the failing case trace has (shown on the Case Medic span)."""
    token, org = env("SENTRY_AUTH_TOKEN"), env("SENTRY_ORG")
    if not (token and org and trace_id):
        return 0
    url = f"{SENTRY_API}/api/0/organizations/{org}/events-trace/{trace_id}/"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers={"Authorization": f"Bearer {token}"})
        body = r.json() if r.status_code == 200 else {}
    except (httpx.HTTPError, ValueError):
        return 0
    return len(body.get("transactions", [])) if isinstance(body, dict) else 0


def trace_headers(alert: Alert) -> dict:
    """Join the failing case's trace. Use the failed span as parent when Sentry gave it to us."""
    if not alert.trace_id:
        return {}
    parent = alert.span_id or uuid.uuid4().hex[:16]
    return {"sentry-trace": f"{alert.trace_id}-{parent}-1"}


@agent.on_rest_post("/alert", Alert, Ack)
async def on_alert(ctx: Context, alert: Alert) -> Ack:
    if alert.token != INTERNAL_TOKEN:
        return Ack(ok=False, detail="bad token")
    dedupe_key = f"sentry-alert:{alert.issue_id}:{alert.check}" if alert.issue_id else ""
    if dedupe_key and ctx.storage.get(dedupe_key):
        metric("count", "billo.medic.duplicate", check=alert.check, action="ignored")
        return Ack(ok=True, detail="already handled")
    action, patient_text = ACTIONS.get(alert.check, ACTIONS["workflow"])
    with case_scope(channel="sentry"):
        if alert.case_id:  # already the keyed hash; never re-hash it
            sentry_sdk.set_tag("case", alert.case_id)
        sentry_sdk.set_tag("check", alert.check)
        sentry_sdk.set_tag("medic.action", action)
        tx = sentry_sdk.continue_trace(trace_headers(alert), op="case_medic.action", name=action)
        with sentry_sdk.start_transaction(tx) as span:
            with sentry_sdk.start_span(op="sentry.api", name="read case trace"):
                transactions = await read_trace(alert.trace_id)
            span.set_data("trace.transactions", transactions)
            span.set_data("issue_id", alert.issue_id)
            ctx.logger.info(f"alert check={alert.check} trace_transactions={transactions} -> {action}")
            metric("count", "billo.medic.alert", check=alert.check, action=action)
            if ADDR["coordinator"] and alert.case_id:
                await ctx.send(ADDR["coordinator"], MedicAction(
                    case_id=alert.case_id, action=action, patient_text=patient_text, trace=carry()))
            elif not alert.case_id:
                # Operational alerts without a keyed case remain diagnostic.
                # Guessing a patient by recency could mutate an unrelated case.
                metric("count", "billo.medic.untagged", check=alert.check, action="ignored")
            if dedupe_key:
                ctx.storage.set(dedupe_key, True)
    return Ack(ok=True, detail=action if alert.case_id else "ignored_missing_case")


if __name__ == "__main__":
    agent.run()
