"""Care Settlement Router: verified clinic QR payments and approved reimbursements."""
import httpx
from uagents import Agent, Context

from common.config import PORTS, READMES, require_seed
from common.core import core_post
from common.models import SettlementRequest, SettlementResult
from common.tracing import carry, case_span, check, init_sentry, metric, task_span

init_sentry("settlement_router")

agent = Agent(
    name="billo-care-settlement-router",
    seed=require_seed("payment_guard"),
    port=PORTS["payment_guard"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "settlement_router.md"),
    description=(
        "Demonstrates clinic Visa QR verification and safeguarded payment or reimbursement handoffs. "
        "All money movement is simulated."
    ),
)


@agent.on_message(model=SettlementRequest)
async def route(ctx: Context, sender: str, req: SettlementRequest):
    reply_to = req.reply_to or sender
    result = SettlementResult(case_id=req.case_id, action=req.action, ok=False, trace=carry())
    try:
        with case_span(req, op="agent.settlement", name=req.action), check("settlement"), task_span(
                "settlement-guard", "settlement.guard", 3000, action=req.action, route="settlement"):
            if req.action == "inspect_qr":
                data = await core_post("/visa/qr/inspect", {
                    "case_id": req.case_id, "file_url": req.file_url, "demo": req.demo,
                })
            elif req.action == "approve_qr":
                data = await core_post("/visa/qr/approve", {
                    "case_id": req.case_id, "review_id": req.review_id,
                    "explicit_approval": req.explicit_approval,
                })
            elif req.action == "reimburse":
                data = await core_post("/visa/reimbursement/payout", {
                    "case_id": req.case_id, "benefit_name": req.benefit_name, "amount": req.amount,
                    "benefit_approved": req.benefit_approved,
                    "explicit_patient_approval": req.explicit_approval,
                })
            else:
                raise ValueError("unknown settlement action")
        result = SettlementResult(
            case_id=req.case_id, action=req.action, ok=True, status=data.get("status", ""),
            settlement_id=data.get("settlement_id", ""), trusted=data.get("trusted", False),
            reasons=data.get("reasons", []), merchant_name=data.get("merchant_name", ""),
            amount=data.get("amount", 0), handoff_url=data.get("handoff_url", ""),
            mode=data.get("mode", ""), trace=carry(),
        )
    except (httpx.HTTPError, ValueError) as exc:
        detail = str(exc)
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                detail = exc.response.json().get("detail", detail)
            except ValueError:
                pass
        result.error = detail
    metric("count", "billo.settlement.result", action=req.action,
           result=result.status or ("ok" if result.ok else "blocked"), mode=result.mode or "simulate")
    await ctx.send(reply_to, result)


if __name__ == "__main__":
    agent.run()
