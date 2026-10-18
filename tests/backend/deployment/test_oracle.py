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


def test_only_https_gateway_publishes_host_ports():
    exposed = {name for name, service in services().items() if service.get("ports")}
    assert exposed == {"caddy"}
    assert set(services()["caddy"]["ports"]) == {"80:80", "443:443", "443:443/udp"}


def test_every_service_restarts_after_failure_or_reboot():
    assert all(service.get("restart") == "unless-stopped" for service in services().values())


def test_internal_service_urls_do_not_use_localhost():
    stack = services()
    assert stack["core"]["environment"]["CASE_MEDIC_URL"] == "http://case-medic:8007"
    assert stack["photon"]["environment"]["GATEWAY_URL"] == "http://imessage-gateway:8006"
    assert stack["coordinator"]["environment"]["CORE_URL"] == "http://core:8000"
