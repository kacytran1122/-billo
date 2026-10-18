#!/usr/bin/env python3
"""Production smoke test that never prints secrets or private response data."""

from __future__ import annotations

import json
import secrets
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


def fetch(url: str, token: str = "", payload: dict | None = None) -> tuple[int, dict[str, str], bytes]:
    headers = {"Accept": "application/json", "User-Agent": "BilloProductionSmoke/1.0"}
    if token:
        headers["x-internal-token"] = token
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, headers=headers, data=body, method="POST" if body else "GET")
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()


def json_result(result: tuple[int, dict[str, str], bytes]) -> tuple[dict, dict[str, str]]:
    status, headers, body = result
    if status != 200:
        raise RuntimeError(f"unexpected HTTP status {status}")
    return json.loads(body), headers


def require_private_headers(headers: dict[str, str]) -> None:
    if "no-store" not in headers.get("cache-control", "").lower():
        raise RuntimeError("private screen is missing no-store")
    if "noindex" not in headers.get("x-robots-tag", "").lower():
        raise RuntimeError("private screen is missing noindex")


def smoke(values: dict[str, str]) -> list[str]:
    base = values.get("PUBLIC_BASE_URL", "").rstrip("/")
    web = values.get("PUBLIC_WEB_URL", "").rstrip("/")
    token = values.get("INTERNAL_TOKEN", "")
    if not base.startswith("https://"):
        raise ValueError("PUBLIC_BASE_URL must use HTTPS")
    if not web.startswith("https://"):
        raise ValueError("PUBLIC_WEB_URL must use HTTPS")
    if token == "dev-token" or len(token) < 32:
        raise ValueError("INTERNAL_TOKEN must be a strong production secret")

    health, _ = json_result(fetch(f"{base}/health"))
    if health.get("ok") is not True:
        raise RuntimeError("health check did not report ok")

    query = urllib.parse.urlencode({"q": "knee pain after a fall", "near": "UCLA"})
    care, _ = json_result(fetch(f"{base}/care/search?{query}", token))
    if not care.get("places"):
        raise RuntimeError("care search returned no places")
    place = care["places"][0]

    # Use an isolated synthetic identity. Never print it or any returned private data.
    case_id = f"production-smoke-{secrets.token_hex(8)}"
    estimate, _ = json_result(fetch(f"{base}/estimates", token, {
        "case_id": case_id,
        "npi": place["npi"],
        "place": place["name"],
        "code": care.get("code", "99213"),
        "amount": place["price_typical"],
        "address": place.get("address", ""),
        "hours": place.get("hours", ""),
        "source_label": place.get("price_source", "synthetic smoke estimate"),
        "data_mode": "demo" if values.get("BILLO_MODE", "demo") == "demo" else "live",
    }))
    visit_url = str(estimate.get("visit_url", ""))
    opaque = str(estimate.get("token", ""))
    if not visit_url.startswith(f"{web}/visit/") or case_id in visit_url or len(opaque) != 43:
        raise RuntimeError("estimate did not return a safe private visit URL")

    case_view, case_headers = json_result(fetch(f"{base}/public/cases/{opaque}"))
    require_private_headers(case_headers)
    if case_id in json.dumps(case_view) or case_view.get("provider", {}).get("address") != place.get("address"):
        raise RuntimeError("public case payload is identifying or location-inaccurate")
    directions = str(case_view.get("provider", {}).get("directions_url") or "")
    direction_query = urllib.parse.parse_qs(urllib.parse.urlparse(directions).query)
    if direction_query.get("query") != [place.get("address", "")]:
        raise RuntimeError("case screen directions do not match the conversation location")
    # A care option is not an appointment. Without a user-supplied time, the
    # product must not fabricate an event or offer a calendar download.
    if estimate.get("ics_url") or estimate.get("gcal_url") or case_view.get("calendar") is not None:
        raise RuntimeError("care option invented a calendar time that the conversation did not supply")

    visit_status, visit_headers, _ = fetch(visit_url)
    if visit_status != 200:
        raise RuntimeError("private visit screen did not load")
    require_private_headers(visit_headers)

    handoff, _ = json_result(fetch(f"{base}/link-codes", token, {
        "case_id": case_id, "channel": "whatsapp_business",
    }))
    if case_id in json.dumps(handoff):
        raise RuntimeError("handoff response exposed its internal case id")
    if handoff.get("available"):
        if not str(handoff.get("deep_link", "")).startswith("https://wa.me/"):
            raise RuntimeError("available WhatsApp handoff is not a wa.me destination")
    elif handoff.get("deep_link") or handoff.get("qr_url"):
        raise RuntimeError("unavailable WhatsApp handoff did not fail closed")
    continue_status, continue_headers, _ = fetch(str(handoff["case_page"]))
    if continue_status != 200:
        raise RuntimeError("private handoff screen did not load")
    require_private_headers(continue_headers)

    checks = [
        "HTTPS health", "authenticated care search", "opaque case snapshot",
        "location-aware directions", "private visit screen", "WhatsApp handoff contract",
    ]

    if values.get("BILLO_MODE", "demo") == "demo":
        invoice = f"SMOKE-{secrets.token_hex(4).upper()}"
        after_request = secrets.token_hex(16)
        json_result(fetch(f"{base}/operations/start", token, {
            "case_id": case_id, "kind": "after_care", "request_id": after_request,
        }))
        json_result(fetch(f"{base}/after-care/organize", token, {
            "case_id": case_id, "request_id": after_request,
            "hospital_npi": place["npi"],
            "payment_status": "unpaid",
            "reader": "demo",
            "document_type": "bill",
            "lines": [{
                "line_no": 1, "code": care.get("code", "99213"),
                "description": "Synthetic smoke-test service", "units": 1,
                "charge": place["price_typical"],
            }],
        }))
        inspect_request = secrets.token_hex(16)
        json_result(fetch(f"{base}/operations/start", token, {
            "case_id": case_id, "kind": "settlement", "request_id": inspect_request,
        }))
        review, _ = json_result(fetch(f"{base}/visa/qr/inspect", token, {
            "case_id": case_id, "request_id": inspect_request,
            "demo": True, "expected_invoice": invoice,
        }))
        approve_request = secrets.token_hex(16)
        json_result(fetch(f"{base}/operations/start", token, {
            "case_id": case_id, "kind": "settlement", "request_id": approve_request,
        }))
        approval, _ = json_result(fetch(f"{base}/visa/qr/approve", token, {
            "case_id": case_id, "request_id": approve_request,
            "review_id": review["settlement_id"], "explicit_approval": True,
        }))
        wallet, wallet_headers = json_result(fetch(str(approval["wallet_api_url"])))
        require_private_headers(wallet_headers)
        if case_id in json.dumps(wallet) or wallet.get("amount") != place["price_typical"]:
            raise RuntimeError("wallet handoff is identifying or has the wrong amount")
        wallet_status, wallet_page_headers, _ = fetch(str(approval["handoff_url"]))
        if wallet_status != 200:
            raise RuntimeError("private wallet screen did not load")
        require_private_headers(wallet_page_headers)
        checks.append("scoped wallet handoff")

    return checks


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
