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
        "BILLO_DOMAIN PUBLIC_BASE_URL SEED_COORDINATOR SEED_RED_FLAG SEED_CARE_FINDER "
        "SEED_BILL_AUDITOR SEED_PAYMENT_GUARD SEED_GATEWAY SEED_CASE_MEDIC ADDR_COORDINATOR "
        "ADDR_RED_FLAG ADDR_CARE_FINDER ADDR_BILL_AUDITOR ADDR_PAYMENT_GUARD ADDR_GATEWAY "
        "ADDR_CASE_MEDIC"
    ).split()
    return {key: "configured" for key in keys}


def test_complete_environment_has_no_blockers():
    blockers, warnings = MODULE.audit(complete_environment())
    assert blockers == []
    assert "VISION_API_KEY" in warnings[0]


def test_missing_signed_webhook_is_a_blocker():
    values = complete_environment()
    values["SENTRY_WEBHOOK_SECRET"] = ""
    values["BILLO_MODE"] = "live"
    blockers, _ = MODULE.audit(values)
    assert blockers == ["SENTRY_WEBHOOK_SECRET"]


def test_demo_mode_is_a_warning_during_staging():
    values = complete_environment() | {
        "BILLO_MODE": "demo",
        "VISION_API_KEY": "configured",
        "SENTRY_WEBHOOK_SECRET": "",
    }
    blockers, warnings = MODULE.audit(values)
    assert blockers == []
    assert warnings == [
        "SENTRY_WEBHOOK_SECRET (required before switching to live mode)",
        "BILLO_MODE (keep demo until the production smoke test passes)",
    ]
