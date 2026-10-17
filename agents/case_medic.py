"""Case Medic (helper): Sentry inside the product loop.

Sentry alert webhook -> Core API /sentry/webhook -> POST /alert here.
1. Read the trace through the Sentry API (if a token is set).
2. Pick ONE of three fixed actions (plain rules, no LLM):
   bill_reader -> retry_reader   (stricter schema / backup model)
   npi         -> npi_unverified (continue with cached data, mark unverified)
   visa        -> pause_guard    (hold payments on this case)
3. Tell the Coordinator, which applies it and texts the patient.
4. Record the action as a span on the same trace.
"""
import httpx
import sentry_sdk
from uagents import Agent, Context

from common.config import ADDR, INTERNAL_TOKEN, PORTS, READMES, env, require_seed
from common.models import Ack, Alert, MedicAction
from common.tracing import carry, init_sentry

init_sentry("case_medic")

ACTIONS = {
    "bill_reader": ("retry_reader", "I am reading your bill again more carefully. One moment."),
    "npi": ("npi_unverified", "One check is slow. I am re-checking, and your case keeps going."),
    "visa": ("pause_guard", "I paused payments on this case for safety. Nothing was charged."),
}

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
    token, org = env("SENTRY_AUTH_TOKEN"), env("SENTRY_ORG")
    if not (token and org and trace_id):
        return 0
    url = f"https://sentry.io/api/0/organizations/{org}/events-trace/{trace_id}/"
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, headers={"Authorization": f"Bearer {token}"})
    return len(r.json().get("transactions", [])) if r.status_code == 200 else 0


@agent.on_rest_post("/alert", Alert, Ack)
async def on_alert(ctx: Context, alert: Alert) -> Ack:
    if alert.token != INTERNAL_TOKEN:
        return Ack(ok=False, detail="bad token")
    action, patient_text = ACTIONS.get(alert.check, ACTIONS["npi"])
    headers = {"sentry-trace": f"{alert.trace_id}-0000000000000000"} if alert.trace_id else {}
    tx = sentry_sdk.continue_trace(headers, op="case_medic.action", name=action)
    with sentry_sdk.start_transaction(tx):
        spans = await read_trace(alert.trace_id)
        sentry_sdk.set_tag("medic.action", action)
        ctx.logger.info(f"alert check={alert.check} trace_spans={spans} -> {action}")
        if ADDR["coordinator"]:  # empty case_id -> Coordinator heals the latest open case
            await ctx.send(ADDR["coordinator"], MedicAction(
                case_id=alert.case_id, action=action, patient_text=patient_text, trace=carry()))
    return Ack(ok=True, detail=action)


if __name__ == "__main__":
    agent.run()
