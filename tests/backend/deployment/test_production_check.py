import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("production_check", ROOT / "deploy" / "check-production.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def complete_environment() -> dict[str, str]:
    keys = (
        "ASI_ONE_API_KEY DATABASE_URL SPECTRUM_PROJECT_ID SPECTRUM_PROJECT_SECRET "
        "PHOTON_LINE_ADDRESS INTERNAL_TOKEN SENTRY_DSN SENTRY_WEBHOOK_SECRET CASE_HASH_KEY "
        "BILLO_DOMAIN PUBLIC_BASE_URL PUBLIC_WEB_URL PUBLIC_LINK_SECRET SEED_COORDINATOR SEED_RED_FLAG SEED_CARE_FINDER "
        "SEED_BILL_AUDITOR SEED_PAYMENT_GUARD SEED_GATEWAY SEED_CASE_MEDIC ADDR_COORDINATOR "
        "ADDR_RED_FLAG ADDR_CARE_FINDER ADDR_BILL_AUDITOR ADDR_PAYMENT_GUARD ADDR_GATEWAY "
        "ADDR_CASE_MEDIC"
    ).split()
    values = {key: "configured" for key in keys}
    values["INTERNAL_TOKEN"] = "i" * 64
    values["SENTRY_WEBHOOK_SECRET"] = "s" * 64
    values["PUBLIC_LINK_SECRET"] = "x" * 64
    values["BILLO_DOMAIN"] = "api.getbillo.us"
    values["PUBLIC_BASE_URL"] = "https://api.getbillo.us"
    values["PUBLIC_WEB_URL"] = "https://www.getbillo.us"
    return values


def test_complete_environment_has_no_blockers():
    blockers, warnings = MODULE.audit(complete_environment())
    assert blockers == []
    assert "VISION_API_KEY" in warnings[0]


def test_missing_signed_webhook_is_a_blocker():
    values = complete_environment()
    values["SENTRY_WEBHOOK_SECRET"] = ""
    values["BILLO_MODE"] = "live"
    blockers, _ = MODULE.audit(values)
    assert blockers == ["SENTRY_WEBHOOK_SECRET (must be at least 32 characters)"]


def test_demo_data_mode_still_requires_signed_webhook():
    values = complete_environment() | {
        "BILLO_MODE": "demo",
        "VISION_API_KEY": "configured",
        "SENTRY_WEBHOOK_SECRET": "",
    }
    blockers, warnings = MODULE.audit(values)
    assert blockers == ["SENTRY_WEBHOOK_SECRET (must be at least 32 characters)"]
    assert warnings == ["BILLO_MODE (keep demo until the production smoke test passes)"]


def test_whatsapp_number_requires_enabled_compatible_transport():
    values = complete_environment() | {
        "PHOTON_WHATSAPP_ADDRESS": "+14155550123",
        "PHOTON_CHANNELS": "imessage",
        "PHOTON_API_VERSION": "beta",
    }
    blockers, _ = MODULE.audit(values)
    assert "PHOTON_CHANNELS (must include whatsapp_business when its number is configured)" in blockers
    assert "PHOTON_API_VERSION (beta transport does not support whatsapp_business)" in blockers


def test_enabled_whatsapp_without_number_warns_and_does_not_fake_availability():
    values = complete_environment() | {"PHOTON_CHANNELS": "imessage,whatsapp_business"}
    blockers, warnings = MODULE.audit(values)
    assert blockers == []
    assert "PHOTON_WHATSAPP_ADDRESS (required to make WhatsApp handoff links available)" in warnings


def test_demo_mode_still_requires_a_strong_public_link_secret():
    values = complete_environment() | {"BILLO_MODE": "demo", "PUBLIC_LINK_SECRET": "too-short"}
    blockers, _ = MODULE.audit(values)
    assert "PUBLIC_LINK_SECRET (must be at least 32 characters)" in blockers


def test_demo_mode_still_requires_a_strong_internal_token():
    values = complete_environment() | {"BILLO_MODE": "demo", "INTERNAL_TOKEN": "too-short"}
    blockers, _ = MODULE.audit(values)
    assert "INTERNAL_TOKEN (must be a non-default secret of at least 32 characters)" in blockers


def test_public_urls_must_be_absolute_https_urls():
    values = complete_environment() | {
        "PUBLIC_BASE_URL": "http://api.getbillo.us",
        "PUBLIC_WEB_URL": "getbillo.us",
    }
    blockers, _ = MODULE.audit(values)
    assert "PUBLIC_BASE_URL (must be an absolute HTTPS URL)" in blockers
    assert "PUBLIC_WEB_URL (must be an absolute HTTPS URL)" in blockers


def test_backend_url_hostname_must_match_caddy_domain():
    values = complete_environment() | {
        "BILLO_DOMAIN": "api.getbillo.us",
        "PUBLIC_BASE_URL": "https://wrong.example.com",
    }
    blockers, _ = MODULE.audit(values)
    assert "PUBLIC_BASE_URL (hostname must match BILLO_DOMAIN)" in blockers


def test_caddy_domain_must_be_a_bare_dns_hostname():
    values = complete_environment() | {"BILLO_DOMAIN": "https://api.getbillo.us/path"}
    blockers, _ = MODULE.audit(values)
    assert "BILLO_DOMAIN (must be a bare DNS hostname)" in blockers
