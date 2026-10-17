"""Bill Auditor + Verifier: live, line by line, with a two-check vote.

1. The Core API reads the bill photo into typed lines (Document Reader).
2. For EACH line, as soon as it is ready:
   - rules check  (duplicates, NCCI pairs, not in the live visit log)
   - price check  (Tiger Data p50/p90 for that code in that area)
   - vote         dispute only if BOTH agree, else "ask the hospital"
   and an AuditUpdate is streamed to the Coordinator right away.
3. Case-level check: total vs. Good Faith Estimate ($400 rule).
4. Final AuditResult (fair amount, disputed amount, charity-care hint).
The AI only reads the photo. Code makes every decision.
"""
import sentry_sdk
from uagents import Agent, Context

from common.config import PORTS, READMES, require_seed
from common.core import core_post
from common.models import AuditRequest, AuditResult, AuditUpdate, BillLine, Flag, dump
from common.tracing import carry, case_span, init_sentry

init_sentry("bill_auditor")

agent = Agent(
    name="billo-bill-auditor",
    seed=require_seed("bill_auditor"),
    port=PORTS["bill_auditor"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "bill_auditor.md"),
    description="Checks a medical bill line by line: duplicates, NCCI code pairs, prices vs. real hospital data, and the $400 Good Faith Estimate rule.",
)


@agent.on_message(model=AuditRequest)
async def on_audit(ctx: Context, sender: str, req: AuditRequest):
    reply_to = req.reply_to or sender
    with case_span(req, op="agent.bill_auditor", name="audit"):
        with sentry_sdk.start_span(op="document.reader", name="read bill"):
            bill = await core_post("/reader/extract", {"case_id": req.case_id, "file_url": req.file_url, "demo": req.demo})
        lines = [BillLine(**l) for l in bill["lines"]]
        npi = bill.get("hospital_npi") or req.hospital_npi

        flags: list[Flag] = []
        at_stake = 0.0
        for line in lines:  # live stream: one update per line
            with sentry_sdk.start_span(op="audit.line", name=f"line {line.line_no}"):
                res = await core_post("/audit/line", {
                    "case_id": req.case_id,
                    "line": dump(line),
                    "all_lines": bill["lines"],
                })
            flag = Flag(**res["flag"]) if res.get("flag") else None
            if flag:
                flags.append(flag)
                if flag.kind == "dispute":
                    at_stake += flag.amount_at_stake
            await ctx.send(reply_to, AuditUpdate(
                case_id=req.case_id, line_no=line.line_no, total_lines=len(lines),
                status=flag.kind if flag else "ok", flag=flag,
                running_total=round(at_stake, 2), text=res["say"], trace=carry(),
            ))

        with sentry_sdk.start_span(op="audit.total", name="good faith estimate"):
            total = await core_post("/audit/total", {"case_id": req.case_id, "lines": bill["lines"], "line_flags": [dump(f) for f in flags]})
        for f in total.get("flags", []):
            flags.append(Flag(**f))

        total_billed = round(sum(l.charge * l.units for l in lines), 2)
        disputed = round(min(total["disputed_amount"], total_billed), 2)
        result = AuditResult(
            case_id=req.case_id, lines=lines, flags=flags, total_billed=total_billed,
            fair_amount=round(total_billed - disputed, 2), disputed_amount=disputed,
            hospital_npi=npi, charity_care_hint=total.get("charity_care_hint", ""),
            reader=bill.get("reader", "unknown"),
            unreviewed_lines=len(bill.get("unreviewed_lines", [])),
            needs_review=bill.get("needs_review", []),
            fallback_reason=bill.get("fallback_reason", ""), trace=carry(),
        )
        ctx.logger.info(f"audit done case={req.case_id[:6]} flags={len(flags)}")
        await ctx.send(reply_to, result)


if __name__ == "__main__":
    agent.run()
