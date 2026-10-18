"""Tiny async client for the Core API (rules, prices, Tiger Data, documents, QR)."""
import httpx
import asyncio
import re

from .config import CORE_URL, INTERNAL_TOKEN
from .tracing import carry

_HEADERS = {"x-internal-token": INTERNAL_TOKEN}
_client = None
_loop = None


async def client():
    """Reuse TCP connections within each agent rather than reconnecting per API call."""
    global _client, _loop
    loop = asyncio.get_running_loop()
    if _client is None or _client.is_closed or _loop is not loop:
        _client = httpx.AsyncClient(base_url=CORE_URL, timeout=60,
                                  limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))
        _loop = loop
    return _client


async def core_get(path: str, **params):
    c = await client()
    r = await c.get(path, params=params, headers={**_HEADERS, **carry()}, timeout=20)
    r.raise_for_status()
    return r.json()


async def core_post(path: str, body: dict):
    c = await client()
    r = await c.post(path, json=body, headers={**_HEADERS, **carry()},
                     timeout=90 if path == "/reader/extract" else 60)
    r.raise_for_status()
    return r.json()


async def core_upload(data: bytes, mime_type: str) -> str:
    """Import bytes into Core's private temporary upload store before OCR."""
    c = await client()
    r = await c.post("/files", content=data, headers={**_HEADERS, **carry(), "content-type": mime_type}, timeout=30)
    r.raise_for_status()
    file_url = r.json().get("file_url", "")
    if not isinstance(file_url, str) or not re.fullmatch(r"file:[A-Za-z0-9_-]+\.[a-z0-9]+", file_url):
        raise ValueError("Core did not accept the document")
    return file_url
