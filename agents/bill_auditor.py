"""After-Care Organizer.

The filename, seed key and port stay stable so existing Agentverse addresses do
not change. The agent turns a receipt or final bill into a verified care record,
reconciles it with the saved estimate and visit log, and tells the Coordinator
whether payment is still needed. Benefits are checked only when the patient
names a real coverage source.
"""
import sentry_sdk
from uagents import Agent, Context

from common.config import PORTS, READMES, require_seed
from common.core import core_post
from common.models import AfterCareRequest, AfterCareResult, BillLine
from common.tracing import carry, case_span, check, init_sentry, metric, task_span

init_sentry("bill_auditor")

agent = Agent(
    name="billo-after-care-organizer",
    seed=require_seed("bill_auditor"),
    port=PORTS["bill_auditor"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "bill_auditor.md"),
    description="Organizes a paid receipt or final bill, matches it to the saved care plan, and prepares safe payment or benefit next steps.",
)


@agent.on_message(model=AfterCareRequest)
async def on_after_care(ctx: Context, sender: str, req: AfterCareRequest):
    reply_to = req.reply_to or sender
    with case_span(req, op="agent.after_care", name="organize receipt"):
        with check("bill_reader", alert_on_4xx=True), task_span(
                "agent-document-reader", "document.reader", 12000, route="after-care") as span:
            bill = await core_post("/reader/extract", {"case_id": req.case_id, "file_url": req.file_url, "demo": req.demo})
            span.set_data("reader", bill.get("reader", "unknown"))
            span.set_data("needs_review", len(bill.get("needs_review", [])))
        metric("count", "billo.reader.path", reader=bill.get("reader", "unknown"), agent="bill_auditor")
        lines = [BillLine(**l) for l in bill["lines"]]
        npi = bill.get("hospital_npi") or req.hospital_npi
        with check("workflow"), task_span(
                "after-care-reconcile", "after_care.reconcile", 2000, route="after-care") as span:
            organized = await core_post("/after-care/organize", {
                "case_id": req.case_id, "lines": bill["lines"], "hospital_npi": npi,
                "payment_status": req.payment_status,
            })
            span.set_data("provider_match", bool(organized["provider_match"]))
            span.set_data("payment_status", req.payment_status)
        result = AfterCareResult(
            case_id=req.case_id, lines=lines, total=organized["total"],
            hospital_npi=npi, payment_status=req.payment_status,
            provider_match=organized["provider_match"],
            estimate_amount=organized.get("estimate_amount"),
            estimate_difference=organized.get("estimate_difference"),
            visit_items_matched=organized["visit_items_matched"],
            next_steps=organized["next_steps"],
            reader=bill.get("reader", "unknown"),
            unreviewed_lines=len(bill.get("unreviewed_lines", [])),
            needs_review=bill.get("needs_review", []),
            fallback_reason=bill.get("fallback_reason", ""), trace=carry(),
        )
        ctx.logger.info(f"after-care record ready case={req.case_id[:6]}")
        await ctx.send(reply_to, result)


if __name__ == "__main__":
    agent.run()
