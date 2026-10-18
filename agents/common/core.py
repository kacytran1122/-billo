"""Tiny async client for the Core API (rules, prices, Tiger Data, documents, QR)."""
import httpx

from .config import CORE_URL, INTERNAL_TOKEN
from .tracing import carry

_HEADERS = {"x-internal-token": INTERNAL_TOKEN}


async def core_get(path: str, **params):
    async with httpx.AsyncClient(base_url=CORE_URL, timeout=20) as c:
        r = await c.get(path, params=params, headers={**_HEADERS, **carry()})
        r.raise_for_status()
        return r.json()


async def core_post(path: str, body: dict):
    async with httpx.AsyncClient(base_url=CORE_URL, timeout=60) as c:
        r = await c.post(path, json=body, headers={**_HEADERS, **carry()})
        r.raise_for_status()
        return r.json()
