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
from common.tracing import carry, case_span, init_sentry, metric, task_span

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
        try:
            result = await organize_document(req)
        except Exception:
            # A malformed/private document must never strand the case or send raw
            # OCR values, signed URLs, or exception messages to logs/telemetry.
            sentry_sdk.set_tag("check", "bill_reader")
            sentry_sdk.capture_message("document reading or organization failed", level="warning")
            metric("count", "billo.reader.failed", reader="none", agent="bill_auditor")
            result = AfterCareResult(
                case_id=req.case_id, request_id=getattr(req, "request_id", ""), ok=False,
                error="document_unreadable", lines=[], total=0,
                hospital_npi="", payment_status=req.payment_status, provider_match=False, trace=carry(),
            )
        await ctx.send(reply_to, result)


def _after_care_result(
        req: AfterCareRequest, organized: dict, *, include_lines: bool = True) -> AfterCareResult:
    """Convert either a fresh or replayed Core record into the worker result."""
    lines = [BillLine(**line) for line in organized.get("lines", [])] if include_lines else []
    needs_review = sorted({
        int(number) for number in organized.get("needs_review", [])
        if str(number).isdigit()
    })
    raw_unreviewed = organized.get("unreviewed_lines", [])
    if isinstance(raw_unreviewed, list):
        unreviewed_count = len({
            int(number) for number in raw_unreviewed if str(number).isdigit()
        })
    else:
        unreviewed_count = max(0, int(raw_unreviewed or 0))
    return AfterCareResult(
        case_id=req.case_id, request_id=getattr(req, "request_id", ""),
        lines=lines, total=organized.get("total", 0),
        hospital_npi=organized.get("hospital_npi", ""),
        payment_status=organized.get("payment_status", "unknown"),
        provider_match=bool(organized.get("provider_match")),
        estimate_amount=organized.get("estimate_amount"),
        estimate_difference=organized.get("estimate_difference"),
        visit_items_matched=organized.get("visit_items_matched", 0),
        next_steps=organized.get("next_steps", []),
        reader=organized.get("reader", "unknown"),
        unreviewed_lines=unreviewed_count, needs_review=needs_review,
        fallback_reason=organized.get("fallback_reason", ""), trace=carry(),
    )


def _inactive_after_care_result(req: AfterCareRequest) -> AfterCareResult:
    return AfterCareResult(
        case_id=req.case_id, request_id=getattr(req, "request_id", ""),
        ok=False, error="operation_inactive", lines=[], total=0,
        hospital_npi="", payment_status=req.payment_status,
        provider_match=False, trace=carry(),
    )


async def organize_document(req: AfterCareRequest) -> AfterCareResult:
    operation = await core_post("/operations/status", {
        "case_id": req.case_id, "kind": "after_care", "request_id": req.request_id,
    })
    if operation.get("status") == "completed":
        replay = operation.get("result")
        if operation.get("action") == "after_care" and isinstance(replay, dict):
            return _after_care_result(req, replay, include_lines=False)
        return _inactive_after_care_result(req)
    if operation.get("status") != "active":
        return _inactive_after_care_result(req)

    with task_span("agent-document-reader", "document.reader", 12000, route="after-care") as span:
        bill = await core_post("/reader/extract", {"case_id": req.case_id, "file_url": req.file_url, "demo": req.demo})
        span.set_data("reader", bill.get("reader", "unknown"))
        span.set_data("needs_review", len(bill.get("needs_review", [])))
    metric("count", "billo.reader.path", reader=bill.get("reader", "unknown"), agent="bill_auditor")
    lines = [BillLine(**line) for line in bill["lines"]]
    valid_line_numbers = {line.line_no for line in lines}
    needs_review = sorted({
        int(number) for number in bill.get("needs_review", [])
        if str(number).isdigit() and int(number) in valid_line_numbers
    })
    # The public case only needs to know which rows were uncoded. Forward line
    # numbers rather than copying the extracted line contents into metadata.
    unreviewed_line_numbers = sorted({
        int(item.get("line_no") if isinstance(item, dict) else item)
        for item in bill.get("unreviewed_lines", [])
        if str(item.get("line_no") if isinstance(item, dict) else item).isdigit()
        and int(item.get("line_no") if isinstance(item, dict) else item) in valid_line_numbers
    })
    # A saved care-plan NPI is not evidence that the uploaded receipt came from
    # that provider. Keep a missing/unreadable document NPI unconfirmed.
    npi = bill.get("hospital_npi") or ""
    with task_span("after-care-reconcile", "after_care.reconcile", 2000, route="after-care") as span:
        document_type = bill.get("document_type") or (
            "receipt" if req.payment_status == "paid" else
            "bill" if req.payment_status == "unpaid" else "unknown"
        )
        organized = await core_post("/after-care/organize", {
            "case_id": req.case_id, "lines": bill["lines"], "hospital_npi": npi,
            "request_id": req.request_id,
            "payment_status": req.payment_status, "reader": bill.get("reader", "unknown"),
            "document_type": document_type,
            "needs_review": needs_review,
            "unreviewed_lines": unreviewed_line_numbers,
            "fallback_reason": str(bill.get("fallback_reason") or "")[:160],
        })
        span.set_data("provider_match", bool(organized["provider_match"]))
        span.set_data("payment_status", req.payment_status)
    return _after_care_result(req, organized)


if __name__ == "__main__":
    agent.run()
