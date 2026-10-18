import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("smoke_test", ROOT / "deploy" / "oracle" / "smoke-test.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


PRIVATE = {"cache-control": "private, no-store", "x-robots-tag": "noindex, nofollow"}


def encoded(payload, headers=None):
    import json
    return 200, headers or {}, json.dumps(payload).encode()


def test_smoke_checks_dynamic_case_location_handoff_and_frontend(monkeypatch):
    seen = []
    place = {
        "name": "Synthetic Clinic", "npi": "1999999901", "price_typical": 240,
        "address": "123 Test Ave", "hours": "open until 9", "price_source": "synthetic",
    }

    def fake_fetch(url, token="", payload=None):
        seen.append((url, token, payload))
        if url.endswith("/health"):
            return encoded({"ok": True})
        if "/care/search?" in url:
            return encoded({"code": "73560", "places": [place]})
        if url.endswith("/estimates"):
            return encoded({
                "token": "x" * 43,
                "visit_url": "https://www.getbillo.us/visit/" + "x" * 43,
            })
        if "/public/cases/" in url:
            return encoded({
                "provider": {
                    "address": place["address"],
                    "directions_url": "https://www.google.com/maps/search/?api=1&query=123%20Test%20Ave",
                },
                "calendar": None,
            }, PRIVATE)
        if url.endswith("/link-codes"):
            return encoded({
                "available": False, "deep_link": "", "qr_url": "",
                "case_page": "https://www.getbillo.us/continue/BILLO-ABCD-2345",
            })
        if "/visit/" in url or "/continue/" in url:
            return 200, PRIVATE, b"private screen"
        raise AssertionError(url)

    monkeypatch.setattr(MODULE, "fetch", fake_fetch)
    passed = MODULE.smoke({
        "PUBLIC_BASE_URL": "https://api.getbillo.us",
        "PUBLIC_WEB_URL": "https://www.getbillo.us",
        "INTERNAL_TOKEN": "s" * 64,
        "BILLO_MODE": "live",
    })
    assert passed == [
        "HTTPS health", "authenticated care search", "opaque case snapshot",
        "location-aware directions", "private visit screen", "WhatsApp handoff contract",
    ]
    assert seen[0] == ("https://api.getbillo.us/health", "", None)
    assert any(url.endswith("/estimates") and auth == "s" * 64 for url, auth, _ in seen)


def test_demo_smoke_checks_scoped_wallet_contract(monkeypatch):
    place = {
        "name": "Synthetic Clinic", "npi": "1999999901", "price_typical": 240,
        "address": "123 Test Ave", "hours": "open until 9", "price_source": "synthetic",
    }

    def fake_fetch(url, token="", payload=None):
        if url.endswith("/health"):
            return encoded({"ok": True})
        if "/care/search?" in url:
            return encoded({"code": "73560", "places": [place]})
        if url.endswith("/estimates"):
            return encoded({
                "token": "x" * 43,
                "visit_url": "https://www.getbillo.us/visit/" + "x" * 43,
            })
        if "/public/cases/" in url:
            return encoded({
                "provider": {
                    "address": place["address"],
                    "directions_url": "https://www.google.com/maps/search/?api=1&query=123%20Test%20Ave",
                },
                "calendar": None,
            }, PRIVATE)
        if url.endswith("/link-codes"):
            return encoded({
                "available": False, "deep_link": "", "qr_url": "",
                "case_page": "https://www.getbillo.us/continue/BILLO-ABCD-2345",
            })
        if url.endswith("/operations/start"):
            return encoded({"ok": True})
        if url.endswith("/after-care/organize"):
            return encoded({"total": 240})
        if url.endswith("/visa/qr/inspect"):
            return encoded({"settlement_id": "qrv_opaque"})
        if url.endswith("/visa/qr/approve"):
            return encoded({
                "wallet_api_url": "https://api.getbillo.us/public/wallet/opaque",
                "handoff_url": "https://www.getbillo.us/wallet/opaque",
            })
        if "/public/wallet/" in url:
            return encoded({"merchant_name": "SYNTHETIC CLINIC", "amount": 240}, PRIVATE)
        if any(part in url for part in ("/visit/", "/continue/", "/wallet/")):
            return 200, PRIVATE, b"private screen"
        raise AssertionError(url)

    monkeypatch.setattr(MODULE, "fetch", fake_fetch)
    assert MODULE.smoke({
        "PUBLIC_BASE_URL": "https://api.getbillo.us",
        "PUBLIC_WEB_URL": "https://www.getbillo.us",
        "INTERNAL_TOKEN": "s" * 64,
        "BILLO_MODE": "demo",
    })[-1] == "scoped wallet handoff"


@pytest.mark.parametrize("base,web", [
    ("", "https://www.getbillo.us"),
    ("http://api.getbillo.us", "https://www.getbillo.us"),
    ("https://api.getbillo.us", "http://www.getbillo.us"),
])
def test_smoke_requires_https(base, web):
    with pytest.raises(ValueError, match="HTTPS"):
        MODULE.smoke({"PUBLIC_BASE_URL": base, "PUBLIC_WEB_URL": web, "INTERNAL_TOKEN": "s" * 64})


def test_smoke_rejects_development_token():
    with pytest.raises(ValueError, match="INTERNAL_TOKEN"):
        MODULE.smoke({
            "PUBLIC_BASE_URL": "https://api.getbillo.us",
            "PUBLIC_WEB_URL": "https://www.getbillo.us",
            "INTERNAL_TOKEN": "dev-token",
        })
