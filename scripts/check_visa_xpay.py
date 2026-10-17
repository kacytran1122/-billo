#!/usr/bin/env python3
"""Verify Visa Developer Platform X-Pay sandbox credentials."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name, value)


def shared_secret() -> bytes:
    direct = os.getenv("VISA_SECRET_KEY", "").strip()
    if direct:
        return direct.encode()
    path = os.getenv("VISA_XPAY_SHARED_SECRET_PATH", "").strip()
    if not path:
        raise SystemExit("Set VISA_SECRET_KEY or VISA_XPAY_SHARED_SECRET_PATH in .env")
    secret_path = Path(path)
    if not secret_path.is_absolute():
        secret_path = ROOT / secret_path
    return secret_path.read_bytes().strip()


def main() -> None:
    load_env()
    api_key = os.getenv("VISA_API_KEY_ID", "").strip()
    if not api_key:
        raise SystemExit("Set VISA_API_KEY_ID in .env")

    timestamp = str(int(time.time()))
    query = urlencode({"apikey": api_key})
    message = (timestamp + "helloworld" + query).encode()
    digest = hmac.new(shared_secret(), message, hashlib.sha256).hexdigest()
    token = f"xv2:{timestamp}:{digest}"
    url = f"https://sandbox.api.visa.com/vdp/helloworld?{query}"
    request = Request(url, headers={"Accept": "application/json", "x-pay-token": token})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
        print(f"Visa X-Pay sandbox OK ({response.status}): {payload['message']}")


if __name__ == "__main__":
    main()
