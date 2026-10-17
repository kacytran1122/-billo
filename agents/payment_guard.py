"""Payment Guard: plain rules in code. It verifies before it pays.

REFUSE if the hospital NPI does not check out (NPI Registry)
REFUSE if the pay link domain is not trusted (hospital, Visa, or heybillo.tech)
REFUSE if the amount is over the patient's signed limit
REFUSE if any disputed money is included
Only then: ask the Core API for a Visa pay link for the fair part only.
"""
from uagents import Agent, Context

from common.config import PORTS, READMES, require_seed
from common.core import core_post
from common.models import PayDecision, PayRequest
from common.tracing import carry, case_span, init_sentry

init_sentry("payment_guard")

agent = Agent(
    name="billo-payment-guard",
    seed=require_seed("payment_guard"),
    port=PORTS["payment_guard"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "payment_guard.md"),
    description="Verifies the hospital and the amount, then pays only the fair part of a medical bill with Visa. Never pays disputed money.",
)


@agent.on_message(model=PayRequest, replies=PayDecision)
async def on_pay(ctx: Context, sender: str, req: PayRequest):
    with case_span(req, op="agent.payment_guard", name="verify and pay"):
        check = await core_post("/guard/verify", {
            "case_id": req.case_id, "npi": req.hospital_npi, "amount": req.amount,
            "disputed_amount": req.disputed_amount, "mandate_max": req.mandate_max, "pay_link": req.pay_link,
        })
        if not check["ok"]:
            await ctx.send(sender, PayDecision(case_id=req.case_id, approved=False, reasons=check["reasons"], trace=carry()))
            return
        link = await core_post("/visa/pay-link", {"case_id": req.case_id, "amount": req.amount})
        await ctx.send(sender, PayDecision(
            case_id=req.case_id, approved=True, reasons=check["reasons"],
            pay_link=link["url"], payment_id=link["payment_id"], trace=carry(),
        ))


if __name__ == "__main__":
    agent.run()
