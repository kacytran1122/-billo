"""Small helpers for the Agent Chat Protocol (what ASI:One speaks)."""
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Context
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    ResourceContent,
    TextContent,
)


def text_of(msg: ChatMessage) -> str:
    return " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()


def resources_of(msg: ChatMessage) -> list[str]:
    """URIs of files the user attached in ASI:One (e.g. a bill photo)."""
    uris = []
    for c in msg.content:
        if isinstance(c, ResourceContent):
            res = c.resource if isinstance(c.resource, list) else [c.resource]
            uris.extend(r.uri for r in res)
    return uris


async def ack(ctx: Context, sender: str, msg: ChatMessage) -> None:
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
    )


async def say(ctx: Context, to: str, text: str, end: bool = False) -> None:
    content = [TextContent(type="text", text=text)]
    if end:
        content.append(EndSessionContent(type="end-session"))
    await ctx.send(to, ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content))
