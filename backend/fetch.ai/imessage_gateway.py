"""iMessage Gateway (helper): a thin adapter, no thinking.

Bridge (Photon Spectrum, TypeScript)  --POST /imessage-->  this agent  --> Coordinator
Coordinator --OutboundText--> this agent --POST {BRIDGE_URL}/send--> Bridge --> iMessage
"""
from uagents import Agent, Context
from uagents_core.types import DeliveryStatus

from common.config import ADDR, BRIDGE_URL, INTERNAL_TOKEN, PORTS, READMES, require_seed
from common.models import Ack, InboundText, OutboundText
from common.core import client as api_client
import sentry_sdk

from common.tracing import carry, case_scope, case_span, init_sentry

init_sentry("gateway")

agent = Agent(
    name="billo-imessage-gateway",
    seed=require_seed("gateway"),
    port=PORTS["gateway"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "gateway.md"),
    description="Helper that connects Billo's iMessage line (Photon) to the Billo Coordinator.",
)


@agent.on_rest_post("/imessage", InboundText, Ack)
async def from_bridge(ctx: Context, req: InboundText) -> Ack:
    if req.token != INTERNAL_TOKEN:
        return Ack(ok=False, detail="bad token")
    if not ADDR["coordinator"]:
        return Ack(ok=False, detail="ADDR_COORDINATOR not set")
    req.token = ""  # never forward secrets
    with case_scope(channel="imessage"):
        tx = sentry_sdk.continue_trace(req.trace or {}, op="gateway.inbound", name="imessage -> coordinator")
        with sentry_sdk.start_transaction(tx) as span:
            span.set_data("group", req.is_group)
            span.set_data("has_file", bool(req.attachment_url))
            req.trace = carry()  # the Coordinator continues from this hop
            delivery = await ctx.send(ADDR["coordinator"], req)
            if delivery.status != DeliveryStatus.DELIVERED:
                span.set_status("internal_error")
                sentry_sdk.set_tag("check", "workflow")
                sentry_sdk.capture_message("gateway could not deliver inbound message to coordinator", level="error")
                return Ack(ok=False, detail="Coordinator delivery failed")
    return Ack(ok=True)


@agent.on_message(model=OutboundText)
async def to_bridge(ctx: Context, sender: str, msg: OutboundText):
    if sender != ADDR["coordinator"]:
        ctx.logger.warning("ignored OutboundText from unknown sender")
        return
    with case_span(msg, op="gateway.outbound", name="coordinator -> imessage"):
        c = await api_client()
        r = await c.post(f"{BRIDGE_URL}/send", json={"space_id": msg.space_id, "text": msg.text},
                         headers={"x-internal-token": INTERNAL_TOKEN, **carry()}, timeout=15)
        if r.status_code >= 400:
            sentry_sdk.set_tag("check", "workflow")
            sentry_sdk.capture_message(f"bridge refused outbound message ({r.status_code})", level="error")


if __name__ == "__main__":
    agent.run()
