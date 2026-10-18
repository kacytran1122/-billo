#!/usr/bin/env python3
"""Production smoke test that never prints secrets or private response data."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def get_json(url: str, token: str = "") -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["x-internal-token"] = token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def smoke(values: dict[str, str]) -> list[str]:
    base = values.get("PUBLIC_BASE_URL", "").rstrip("/")
    token = values.get("INTERNAL_TOKEN", "")
    if not base.startswith("https://"):
        raise ValueError("PUBLIC_BASE_URL must use HTTPS")
    if not token or token == "dev-token":
        raise ValueError("INTERNAL_TOKEN must be configured")

    health = get_json(f"{base}/health")
    if health.get("ok") is not True:
        raise RuntimeError("health check did not report ok")

    query = urllib.parse.urlencode({"q": "knee pain after a fall", "near": "UCLA"})
    care = get_json(f"{base}/care/search?{query}", token)
    if not care.get("places"):
        raise RuntimeError("care search returned no places")

    return ["HTTPS health", "authenticated care search"]


def main() -> int:
    try:
        passed = smoke(read_env(ROOT / ".env"))
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"Smoke test failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    for check in passed:
        print(f"PASS: {check}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
