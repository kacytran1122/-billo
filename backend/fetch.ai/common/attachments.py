"""Bounded, private-network-safe ingestion of ASI:One document resources."""
from __future__ import annotations

import asyncio
import base64
import binascii
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx


MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
DOCUMENT_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "application/pdf"}


class AttachmentError(ValueError):
    """A safe category only: never retain a private document URI or response body."""


@dataclass(frozen=True)
class ChatAttachment:
    uri: str
    mime_type: str = ""


def _document_mime(data: bytes) -> str:
    if not data:
        raise AttachmentError("empty")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise AttachmentError("too_large")
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.lstrip().startswith(b"%PDF-"):
        return "application/pdf"
    if data[4:8] == b"ftyp" and data[8:12] in {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1", b"heif"}:
        return "image/heic" if data[8:12].startswith(b"hei") and data[8:12] != b"heif" else "image/heif"
    raise AttachmentError("unsupported_type")


def _inline_document(uri: str) -> tuple[bytes, str]:
    # Reject an oversized encoding before allocating its decoded bytes.
    if len(uri) > ((MAX_DOCUMENT_BYTES + 2) // 3) * 4 + 128:
        raise AttachmentError("too_large")
    header, separator, encoded = uri.partition(",")
    if not separator or not header.lower().endswith(";base64"):
        raise AttachmentError("invalid_inline")
    mime = header[5:].split(";", 1)[0].lower()
    if mime not in DOCUMENT_MIMES:
        raise AttachmentError("unsupported_type")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise AttachmentError("invalid_inline") from None
    actual = _document_mime(data)
    if actual != mime and {actual, mime} != {"image/heic", "image/heif"}:
        raise AttachmentError("unsupported_type")
    return data, actual


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return (
        ip.is_global and not ip.is_multicast and not ip.is_unspecified and not ip.is_reserved
        and not getattr(ip, "is_site_local", False)
        and not getattr(ip, "ipv4_mapped", None)
        and not getattr(ip, "sixtofour", None)
        and not getattr(ip, "teredo", None)
    )


async def _pinned_destination(uri: str) -> tuple[httpx.URL, str]:
    try:
        if len(uri) > 8192 or any(ord(character) < 32 or ord(character) == 127 for character in uri):
            raise AttachmentError("unsupported_uri")
        parsed = urlsplit(uri)
        if (parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.fragment or parsed.port not in (None, 443)):
            raise AttachmentError("unsupported_uri")
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii")
        if not host or "%" in host or len(host) > 253:
            raise AttachmentError("unsupported_uri")
        try:
            ipaddress.ip_address(host)
            addresses = {host}
        except ValueError:
            resolved = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            addresses = {item[4][0] for item in resolved}
        # Reject mixed public/private answers, then connect to this exact public IP.
        # The HTTP client never resolves the untrusted hostname a second time.
        if not addresses or any(not _is_public(address) for address in addresses):
            raise AttachmentError("unsafe_destination")
        pinned = httpx.URL(uri).copy_with(host=sorted(addresses)[0])
        return pinned, host
    except AttachmentError:
        raise
    except (OSError, ValueError, UnicodeError):
        raise AttachmentError("unavailable") from None


async def _remote_document(uri: str) -> tuple[bytes, str]:
    pinned, host = await _pinned_destination(uri)
    request = httpx.Request(
        "GET", pinned,
        headers={"host": f"[{host}]" if ":" in host else host, "accept-encoding": "identity"},
        extensions={"sni_hostname": host, "timeout": {"connect": 10, "read": 20, "write": 10, "pool": 5}},
    )
    # A dedicated transport has no application auth, cookies, environment proxies,
    # redirects, or HTTPX client request logger (which would expose signed URLs).
    async with httpx.AsyncHTTPTransport(retries=0, trust_env=False) as transport:
        response = await transport.handle_async_request(request)
        try:
            if response.status_code != 200:
                raise AttachmentError("unavailable")
            length = response.headers.get("content-length")
            if length and (not length.isdigit() or int(length) > MAX_DOCUMENT_BYTES):
                raise AttachmentError("too_large")
            data = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                if len(data) + len(chunk) > MAX_DOCUMENT_BYTES:
                    raise AttachmentError("too_large")
                data.extend(chunk)
            body = bytes(data)
            return body, _document_mime(body)
        finally:
            await response.aclose()


async def document_bytes(attachment: ChatAttachment) -> tuple[bytes, str]:
    """Accept inline data or a public HTTPS document, never a local/storage path."""
    try:
        if attachment.uri[:5].lower() == "data:":
            return _inline_document(attachment.uri)
        return await asyncio.wait_for(_remote_document(attachment.uri), timeout=30)
    except AttachmentError:
        raise
    except (OSError, ValueError, httpx.HTTPError, asyncio.TimeoutError):
        raise AttachmentError("unavailable") from None
