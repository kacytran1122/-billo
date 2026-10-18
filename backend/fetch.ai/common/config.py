"""Shared settings for every Billo agent. Reads the repo-root .env once."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


MODE = env("BILLO_MODE", "demo")  # demo | live
CORE_URL = env("CORE_URL", "http://localhost:8000")
BRIDGE_URL = env("BRIDGE_URL", "http://localhost:3000")
INTERNAL_TOKEN = env("INTERNAL_TOKEN", "dev-token")
FOLLOWUP_MINUTES = float(env("FOLLOWUP_MINUTES", "30"))

ASI_ONE_API_KEY = env("ASI_ONE_API_KEY")
ASI_ONE_BASE_URL = env("ASI_ONE_BASE_URL", "https://api.asi1.ai/v1")
ASI_ONE_MODEL = env("ASI_ONE_MODEL", "asi1")

# Ports (one per agent, so they can run side by side on one laptop)
PORTS = {
    "coordinator": 8001,
    "red_flag": 8002,
    "care_finder": 8003,
    "bill_auditor": 8004,
    "payment_guard": 8005,  # retained seed/address key; runtime name is Care Settlement Router
    "gateway": 8006,
    "case_medic": 8007,
}

SEEDS = {
    "coordinator": env("SEED_COORDINATOR"),
    "red_flag": env("SEED_RED_FLAG"),
    "care_finder": env("SEED_CARE_FINDER"),
    "bill_auditor": env("SEED_BILL_AUDITOR"),
    "payment_guard": env("SEED_PAYMENT_GUARD"),
    "gateway": env("SEED_GATEWAY"),
    "case_medic": env("SEED_CASE_MEDIC"),
}

ADDR = {
    "coordinator": env("ADDR_COORDINATOR"),
    "red_flag": env("ADDR_RED_FLAG"),
    "care_finder": env("ADDR_CARE_FINDER"),
    "bill_auditor": env("ADDR_BILL_AUDITOR"),
    "payment_guard": env("ADDR_PAYMENT_GUARD"),
    "gateway": env("ADDR_GATEWAY"),
    "case_medic": env("ADDR_CASE_MEDIC"),
}

READMES = BACKEND_ROOT / "fetch.ai" / "readmes"


def require_seed(key: str) -> str:
    seed = SEEDS[key]
    if not seed or "CHANGE-ME" in seed:
        raise SystemExit(f"Set a unique SEED_{key.upper()} in .env before running this agent.")
    return seed
