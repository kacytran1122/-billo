#!/usr/bin/env python3
"""Report production readiness without printing secret values."""

from __future__ import annotations

import sys
from pathlib import Path


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
    if values.get("INTERNAL_TOKEN") == "dev-token":
        blockers.append("INTERNAL_TOKEN (still dev-token)")

    warnings: list[str] = []
    live = values.get("BILLO_MODE", "demo") == "live"
    if live and not values.get("SENTRY_WEBHOOK_SECRET"):
        blockers.append("SENTRY_WEBHOOK_SECRET")
    elif not values.get("SENTRY_WEBHOOK_SECRET"):
        warnings.append("SENTRY_WEBHOOK_SECRET (required before switching to live mode)")
    if not values.get("VISION_API_KEY"):
        warnings.append("VISION_API_KEY (optional fallback; local OCR remains enabled)")
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
