from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "deploy" / "oracle" / "compose.yml"
HOST_PROXY_COMPOSE = ROOT / "deploy" / "oracle" / "compose.host-proxy.yml"
INSTALL = ROOT / "deploy" / "oracle" / "install.sh"
CADDYFILE = ROOT / "deploy" / "oracle" / "Caddyfile"
HOST_CADDYFILE = ROOT / "deploy" / "oracle" / "Caddyfile.host"
CLOUD_INIT = ROOT / "deploy" / "oracle" / "cloud-init.yaml"
CORE_DOCKERFILE = ROOT / "Dockerfile"


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


def test_only_https_gateway_is_published_by_default():
    stack = services()
    default_exposed = {
        name for name, service in stack.items()
        if service.get("ports") and not service.get("profiles")
    }
    assert default_exposed == {"caddy"}
    assert "ports" not in stack["core"]
    assert stack["core"]["expose"] == ["8000"]
    assert "profiles" not in stack["caddy"]
    assert set(services()["caddy"]["ports"]) == {"80:80", "443:443", "443:443/udp"}


def test_caddy_uses_configured_dns_name_and_private_core_upstream():
    config = CADDYFILE.read_text()
    assert "{$BILLO_DOMAIN}" in config
    assert "reverse_proxy core:8000" in config
    assert services()["caddy"]["env_file"] == "../../.env"
    assert set(services()["caddy"]["networks"]) == {"billo"}


def test_host_caddy_template_uses_loopback_and_same_security_headers():
    docker_config = CADDYFILE.read_text()
    host_config = HOST_CADDYFILE.read_text()
    assert "__BILLO_DOMAIN__" in host_config
    assert "{$BILLO_DOMAIN}" not in host_config
    assert "reverse_proxy 127.0.0.1:8000" in host_config
    assert "reverse_proxy core:8000" not in host_config
    for directive in (
        'Strict-Transport-Security "max-age=31536000; includeSubDomains"',
        'X-Content-Type-Options "nosniff"',
        'Referrer-Policy "strict-origin-when-cross-origin"',
        "-Server",
    ):
        assert directive in docker_config
        assert directive in host_config


def test_cloud_init_only_opens_public_gateway_ports():
    config = CLOUD_INIT.read_text()
    assert "ufw allow 80/tcp" in config
    assert "ufw allow 443/tcp" in config
    assert "ufw allow 443/udp" in config
    assert "8000" not in config


def test_host_caddy_compatibility_override_is_loopback_only():
    override = yaml.safe_load(HOST_PROXY_COMPOSE.read_text())["services"]
    assert override["core"]["ports"] == ["127.0.0.1:8000:8000"]
    assert override["caddy"]["profiles"] == ["docker-gateway"]


def test_every_service_restarts_after_failure_or_reboot():
    assert all(service.get("restart") == "unless-stopped" for service in services().values())


def test_chat_runtime_services_have_healthchecks_and_ordered_dependencies():
    stack = services()
    agents = {
        "coordinator", "red-flag", "care-finder", "bill-auditor",
        "settlement-router", "imessage-gateway", "case-medic",
    }
    assert all(stack[name].get("healthcheck", {}).get("test") for name in agents)
    assert stack["photon"].get("healthcheck", {}).get("test")
    assert stack["photon"]["depends_on"]["imessage-gateway"]["condition"] == "service_healthy"
    assert stack["imessage-gateway"]["depends_on"]["coordinator"]["condition"] == "service_healthy"
    for dependency in ("red-flag", "care-finder", "bill-auditor", "settlement-router"):
        assert stack["coordinator"]["depends_on"][dependency]["condition"] == "service_healthy"


def test_internal_service_urls_do_not_use_localhost():
    stack = services()
    assert stack["core"]["environment"]["CASE_MEDIC_URL"] == "http://case-medic:8007"
    assert stack["photon"]["environment"]["GATEWAY_URL"] == "http://imessage-gateway:8006"
    assert stack["coordinator"]["environment"]["CORE_URL"] == "http://core:8000"


def test_install_applies_idempotent_database_schema_before_services_start():
    script = INSTALL.read_text()
    stop = 'stop -t 30 coordinator bill-auditor settlement-router imessage-gateway photon'
    migration = 'run --rm core python backend/scripts/apply_schema.py'
    assert stop in script
    assert migration in script
    assert script.index(stop) < script.index(migration)
    assert script.index(migration) < script.index('up -d --remove-orphans')
    assert 'up -d --remove-orphans --wait --wait-timeout 180' in script


def test_install_defaults_to_docker_gateway_but_preserves_active_host_caddy_upgrades():
    script = INSTALL.read_text()
    assert 'proxy_mode="${BILLO_PROXY_MODE:-auto}"' in script
    assert "systemctl is-active --quiet caddy" in script
    assert 'compose+=(-f "$HOST_PROXY_COMPOSE")' in script
    assert 'pull caddy' in script
    assert 'caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile' in script
    assert 'ps --status running -q caddy' in script


def test_host_caddy_install_is_privileged_atomic_validated_and_rollback_safe():
    script = INSTALL.read_text()
    assert 'if [[ "$EUID" -ne 0 ]]' in script
    assert 'sudo env BILLO_PROXY_MODE=host deploy/oracle/install.sh' in script
    assert 'systemctl show -p ExecStart --value caddy' in script
    assert 'sed "s/__BILLO_DOMAIN__/$billo_domain/g"' in script
    assert 'caddy validate --config "$host_caddy_candidate" --adapter caddyfile' in script
    assert 'cp --preserve=mode,ownership,timestamps -- "$HOST_CADDY_CONFIG" "$backup"' in script
    assert 'mv -f -- "$host_caddy_candidate" "$HOST_CADDY_CONFIG"' in script
    assert 'systemctl reload caddy' in script
    assert 'restoring $backup' in script
    assert 'mv -f -- "$rollback_candidate" "$HOST_CADDY_CONFIG"' in script


def test_core_disables_access_logs_that_would_capture_bearer_paths():
    command = CORE_DOCKERFILE.read_text()
    assert "--no-access-log" in command
