"""Care Finder: nearby care sites and price context from the Core API."""
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec

from common.chat import ack, say, text_of
from common.config import PORTS, READMES, require_seed
from common.core import core_get
from common.models import CareOptions, FindCareRequest, Place
from common.tracing import carry, case_span, init_sentry

init_sentry("care_finder")

agent = Agent(
    name="billo-care-finder",
    seed=require_seed("care_finder"),
    port=PORTS["care_finder"],
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(READMES / "care_finder.md"),
    description="Finds urgent care, clinics and ERs near you with real hospital price context.",
)


async def find(text: str, near: str) -> CareOptions:
    data = await core_get("/care/search", q=text, near=near)
    return CareOptions(case_id="", code=data["code"], places=[Place(**p) for p in data["places"]])


def as_text(opts: CareOptions, group_safe: bool) -> str:
    head = "Here are 3 places nearby, with real prices:" if group_safe else \
        f"Here are {len(opts.places)} places near you for this (billing code {opts.code}):"
    rows = [
        f"{i}. {p.name} · about ${p.price_typical:,.0f} (low ${p.price_low:,.0f}) · {p.hours}\n   {p.address}"
        for i, p in enumerate(opts.places, 1)
    ]
    tail = "" if group_safe else "\nReply with the number to book, for example: book 1"
    return "\n".join([head, *rows]) + tail + "\nPrices come from public hospital price files."


@agent.on_message(model=FindCareRequest, replies=CareOptions)
async def on_find(ctx: Context, sender: str, req: FindCareRequest):
    with case_span(req, op="agent.care_finder", name="find"):
        opts = await find(req.text, req.near)
        opts.case_id = req.case_id
        opts.trace = carry()
        await ctx.send(sender, opts)


chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ack(ctx, sender, msg)
    opts = await find(text_of(msg), "UCLA, Los Angeles, CA")
    await say(ctx, sender, as_text(opts, group_safe=True))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
