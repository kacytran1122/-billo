"""Opaque, scoped public-link tokens.

Tokens are deterministic HMAC-SHA256 values so a case keeps the same visit URL
when a conversation is resumed.  Only a second SHA-256 digest of each token is
stored; the bearer token itself exists only in the returned URL.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlparse


CASE_SCOPE = "case_view"
WALLET_SCOPE = "wallet_handoff"
LETTER_SCOPE = "dispute_letter"
INVOICE_SCOPE = "invoice_reference"


def _secret() -> bytes:
    configured = os.getenv("PUBLIC_LINK_SECRET", "").strip()
    if len(configured) >= 32:
        return configured.encode()
    internal = os.getenv("INTERNAL_TOKEN", "").strip()
    if len(internal) >= 32 and internal != "dev-token":
        return internal.encode()
    hostname = (urlparse(os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")).hostname or "").lower()
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError(
            "PUBLIC_LINK_SECRET or a strong INTERNAL_TOKEN is required for non-local public links"
        )
    # Local-only runs remain turnkey. Never use this key for a public hostname,
    # even when BILLO_MODE=demo (production currently uses demo data mode).
    return b"billo-local-public-link-secret"


def derive(scope: str, subject: str) -> str:
    """Return a URL-safe, full 256-bit HMAC token without padding."""
    message = f"billo-public-link-v1\x00{scope}\x00{subject}".encode()
    digest = hmac.new(_secret(), message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def token_hash(token: str) -> str:
    """Return the only representation of a bearer token that may be stored."""
    return hashlib.sha256(token.encode()).hexdigest()


def expires_in(seconds: int) -> float:
    return time.time() + seconds


def iso_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")

