"""iMessage Gateway (helper): a thin adapter, no thinking.

Bridge (Photon Spectrum, TypeScript)  --POST /imessage-->  this agent  --> Coordinator
Coordinator --OutboundText--> this agent --POST {BRIDGE_URL}/send--> Bridge --> iMessage
"""
import httpx
from uagents import Agent, Context

from common.config import ADDR, BRIDGE_URL, INTERNAL_TOKEN, PORTS, READMES, require_seed
from common.models import Ack, InboundText, OutboundText
from common.tracing import init_sentry

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
    await ctx.send(ADDR["coordinator"], req)
    return Ack(ok=True)


@agent.on_message(model=OutboundText)
async def to_bridge(ctx: Context, sender: str, msg: OutboundText):
    if sender != ADDR["coordinator"]:
        ctx.logger.warning("ignored OutboundText from unknown sender")
        return
    async with httpx.AsyncClient(timeout=15) as c:
        await c.post(f"{BRIDGE_URL}/send", json={"space_id": msg.space_id, "text": msg.text},
                     headers={"x-internal-token": INTERNAL_TOKEN})


if __name__ == "__main__":
    agent.run()
