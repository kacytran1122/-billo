"""Small helpers for the Agent Chat Protocol (what ASI:One speaks)."""
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Context
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    MetadataContent,
    ResourceContent,
    StartSessionContent,
    TextContent,
)

from .attachments import AttachmentError, ChatAttachment, document_bytes
from .core import core_upload


def text_of(msg: ChatMessage) -> str:
    return " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()


def resources_of(msg: ChatMessage) -> list[ChatAttachment]:
    """Select each primary document, not accompanying thumbnails/audio tracks.

    ChatProtocol resources may carry the downloadable URI in their metadata
    instead of ``uri``. An opaque storage reference alone is not a readable file.
    """
    resources = []
    for c in msg.content:
        if isinstance(c, ResourceContent):
            res = c.resource if isinstance(c.resource, list) else [c.resource]
            if not res:
                raise AttachmentError("missing_resource")
            primary = res[0]
            metadata = primary.metadata or {}
            candidates = [primary.uri] + [metadata.get(key, "") for key in ("url", "uri", "source", "image_url", "download_url", "file_url")]
            uri = next((value.strip() for value in candidates if isinstance(value, str) and value.strip().lower().startswith(("https://", "data:"))), "")
            if not uri:
                raise AttachmentError("unsupported_uri")
            resources.append(ChatAttachment(uri=uri, mime_type=metadata.get("mime_type", "")))
    return resources


async def upload_resources(msg: ChatMessage) -> list[str]:
    resources = resources_of(msg)
    if len(resources) > 1:
        raise AttachmentError("multiple_documents")
    if not resources:
        return []
    data, mime_type = await document_bytes(resources[0])
    try:
        return [await core_upload(data, mime_type)]
    except Exception:
        raise AttachmentError("upload_failed") from None


async def advertise_attachments(ctx: Context, sender: str, msg: ChatMessage) -> None:
    """Enable ASI:One's attachment control at the start of a chat session."""
    if any(isinstance(content, StartSessionContent) for content in msg.content):
        await ctx.send(sender, ChatMessage(content=[MetadataContent(metadata={"attachments": "true"})]))


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
