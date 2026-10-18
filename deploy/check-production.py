#!/usr/bin/env python3
"""Report production readiness without printing secret values."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def audit(values: dict[str, str]) -> tuple[list[str], list[str]]:
    required = (
        "ASI_ONE_API_KEY",
        "DATABASE_URL",
        "SPECTRUM_PROJECT_ID",
        "SPECTRUM_PROJECT_SECRET",
        "PHOTON_LINE_ADDRESS",
        "INTERNAL_TOKEN",
        "SENTRY_DSN",
        "CASE_HASH_KEY",
        "BILLO_DOMAIN",
        "PUBLIC_BASE_URL",
        "PUBLIC_WEB_URL",
        "PUBLIC_LINK_SECRET",
        "SEED_COORDINATOR",
        "SEED_RED_FLAG",
        "SEED_CARE_FINDER",
        "SEED_BILL_AUDITOR",
        "SEED_PAYMENT_GUARD",
        "SEED_GATEWAY",
        "SEED_CASE_MEDIC",
        "ADDR_COORDINATOR",
        "ADDR_RED_FLAG",
        "ADDR_CARE_FINDER",
        "ADDR_BILL_AUDITOR",
        "ADDR_PAYMENT_GUARD",
        "ADDR_GATEWAY",
        "ADDR_CASE_MEDIC",
    )
    blockers = [key for key in required if not values.get(key) or "CHANGE-ME" in values[key]]
    internal_token = values.get("INTERNAL_TOKEN", "")
    if internal_token == "dev-token" or len(internal_token) < 32:
        blockers.append("INTERNAL_TOKEN (must be a non-default secret of at least 32 characters)")
    # Production intentionally still uses demo *data*. Bearer-link security is
    # independent of data mode, so a weak key is always a deployment blocker.
    if len(values.get("PUBLIC_LINK_SECRET", "")) < 32:
        blockers.append("PUBLIC_LINK_SECRET (must be at least 32 characters)")
    parsed_urls = {}
    for key in ("PUBLIC_BASE_URL", "PUBLIC_WEB_URL"):
        parsed = urlparse(values.get(key, ""))
        parsed_urls[key] = parsed
        if parsed.scheme != "https" or not parsed.hostname:
            blockers.append(f"{key} (must be an absolute HTTPS URL)")

    domain = values.get("BILLO_DOMAIN", "").strip().rstrip(".").lower()
    parsed_domain = urlparse(f"//{domain}")
    valid_domain = (
        bool(domain)
        and "." in domain
        and parsed_domain.hostname == domain
        and not parsed_domain.path
    )
    if not valid_domain:
        blockers.append("BILLO_DOMAIN (must be a bare DNS hostname)")
    elif parsed_urls["PUBLIC_BASE_URL"].hostname != domain:
        blockers.append("PUBLIC_BASE_URL (hostname must match BILLO_DOMAIN)")

    whatsapp_address = values.get("PHOTON_WHATSAPP_ADDRESS", "").strip()
    photon_channels = {
        channel.strip() for channel in values.get("PHOTON_CHANNELS", "").split(",") if channel.strip()
    }
    photon_beta = values.get("PHOTON_API_VERSION", "").strip().lower() == "beta"
    whatsapp_enabled = "whatsapp_business" in photon_channels
    whatsapp_digits = re.sub(r"\D", "", whatsapp_address)
    if whatsapp_address:
        if not re.fullmatch(r"[1-9]\d{7,14}", whatsapp_digits):
            blockers.append("PHOTON_WHATSAPP_ADDRESS (must be a valid international number)")
        if not whatsapp_enabled:
            blockers.append("PHOTON_CHANNELS (must include whatsapp_business when its number is configured)")
        if photon_beta:
            blockers.append("PHOTON_API_VERSION (beta transport does not support whatsapp_business)")

    warnings: list[str] = []
    live = values.get("BILLO_MODE", "demo") == "live"
    if len(values.get("SENTRY_WEBHOOK_SECRET", "")) < 32:
        blockers.append("SENTRY_WEBHOOK_SECRET (must be at least 32 characters)")
    if not values.get("VISION_API_KEY"):
        warnings.append("VISION_API_KEY (optional fallback; local OCR remains enabled)")
    if whatsapp_enabled and not whatsapp_address:
        warnings.append("PHOTON_WHATSAPP_ADDRESS (required to make WhatsApp handoff links available)")
    if whatsapp_enabled and photon_beta and not whatsapp_address:
        warnings.append("PHOTON_API_VERSION (beta transport does not support whatsapp_business)")
    if not live:
        warnings.append("BILLO_MODE (keep demo until the production smoke test passes)")
    return sorted(set(blockers)), warnings


def main() -> int:
    values = read_env(ROOT / ".env")
    blockers, warnings = audit(values)
    print(f"Production blockers: {len(blockers)}")
    for item in blockers:
        print(f"  - {item}")
    print(f"Warnings: {len(warnings)}")
    for item in warnings:
        print(f"  - {item}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
