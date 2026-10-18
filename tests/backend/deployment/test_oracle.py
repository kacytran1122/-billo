from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "deploy" / "oracle" / "compose.yml"


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def test_oracle_stack_contains_every_backend_layer():
    assert set(services()) == {
        "core",
        "coordinator",
        "red-flag",
        "care-finder",
        "bill-auditor",
        "settlement-router",
        "imessage-gateway",
        "case-medic",
        "photon",
        "caddy",
    }


def test_only_loopback_core_is_published_by_default_and_https_gateway_is_opt_in():
    stack = services()
    default_exposed = {
        name for name, service in stack.items()
        if service.get("ports") and not service.get("profiles")
    }
    assert default_exposed == {"core"}
    assert stack["core"]["ports"] == ["127.0.0.1:8000:8000"]
    assert stack["caddy"]["profiles"] == ["docker-gateway"]
    assert set(services()["caddy"]["ports"]) == {"80:80", "443:443", "443:443/udp"}


def test_every_service_restarts_after_failure_or_reboot():
    assert all(service.get("restart") == "unless-stopped" for service in services().values())


def test_internal_service_urls_do_not_use_localhost():
    stack = services()
    assert stack["core"]["environment"]["CASE_MEDIC_URL"] == "http://case-medic:8007"
    assert stack["photon"]["environment"]["GATEWAY_URL"] == "http://imessage-gateway:8006"
    assert stack["coordinator"]["environment"]["CORE_URL"] == "http://core:8000"
