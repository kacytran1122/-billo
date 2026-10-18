"""Tiny async client for the Core API (rules, prices, Tiger Data, documents, QR)."""
import httpx
import asyncio

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
    r = await c.post(path, json=body, headers={**_HEADERS, **carry()})
    r.raise_for_status()
    return r.json()
