#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="$ROOT/deploy/oracle/compose.yml"
HOST_PROXY_COMPOSE="$ROOT/deploy/oracle/compose.host-proxy.yml"
HOST_CADDY_TEMPLATE="$ROOT/deploy/oracle/Caddyfile.host"
HOST_CADDY_CONFIG="/etc/caddy/Caddyfile"
host_caddy_candidate=""

cleanup() {
  if [[ -n "$host_caddy_candidate" && -e "$host_caddy_candidate" ]]; then
    rm -f -- "$host_caddy_candidate"
  fi
}
trap cleanup EXIT

if [[ ! -f "$ROOT/.env" ]]; then
  echo "Missing $ROOT/.env. Copy .env.example, then add production secrets." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed yet. Wait for cloud-init to finish, then retry." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is not available." >&2
  exit 1
fi

# Docker Caddy is the canonical ingress. Auto-detection keeps upgrades safe on
# older Billo hosts where a system Caddy service already owns ports 80/443.
proxy_mode="${BILLO_PROXY_MODE:-auto}"
host_caddy_active=false
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet caddy; then
  host_caddy_active=true
fi

if [[ "$proxy_mode" == "auto" ]]; then
  if [[ "$host_caddy_active" == "true" ]]; then
    proxy_mode="host"
  else
    proxy_mode="docker"
  fi
fi

if [[ "$proxy_mode" != "docker" && "$proxy_mode" != "host" ]]; then
  echo "BILLO_PROXY_MODE must be auto, docker, or host." >&2
  exit 1
fi

if [[ "$proxy_mode" == "docker" && "$host_caddy_active" == "true" ]]; then
  echo "System Caddy is already active on ports 80/443." >&2
  echo "Use BILLO_PROXY_MODE=host for this upgrade, or stop and disable system Caddy before migrating to Docker Caddy." >&2
  exit 1
fi

compose=(docker compose -f "$COMPOSE")
if [[ "$proxy_mode" == "host" ]]; then
  if [[ "$host_caddy_active" != "true" ]]; then
    echo "BILLO_PROXY_MODE=host requires an active system Caddy service." >&2
    exit 1
  fi
  if [[ "$EUID" -ne 0 ]]; then
    echo "BILLO_PROXY_MODE=host must run as root so the installer can safely update and reload system Caddy." >&2
    echo "Run: sudo env BILLO_PROXY_MODE=host deploy/oracle/install.sh" >&2
    exit 1
  fi
  if ! command -v caddy >/dev/null 2>&1; then
    echo "BILLO_PROXY_MODE=host requires the caddy command." >&2
    exit 1
  fi
  if [[ ! -f "$HOST_CADDY_CONFIG" || -L "$HOST_CADDY_CONFIG" ]]; then
    echo "Expected a regular system Caddy configuration at $HOST_CADDY_CONFIG; refusing to replace it." >&2
    exit 1
  fi
  if [[ ! -f "$HOST_CADDY_TEMPLATE" ]]; then
    echo "Missing host Caddy template: $HOST_CADDY_TEMPLATE" >&2
    exit 1
  fi
  caddy_unit="$(systemctl show -p ExecStart --value caddy 2>/dev/null || true)"
  if [[ "$caddy_unit" != *"$HOST_CADDY_CONFIG"* ]]; then
    echo "The active caddy service does not use $HOST_CADDY_CONFIG; refusing to update an unrelated file." >&2
    exit 1
  fi
  compose+=(-f "$HOST_PROXY_COMPOSE")
  echo "Using the existing system Caddy service with Core bound to 127.0.0.1:8000."
else
  echo "Using the canonical Docker Caddy HTTPS gateway."
fi

cd "$ROOT"
python3 deploy/check-production.py

if [[ "$proxy_mode" == "host" ]]; then
  billo_domain="$(sed -n 's/^[[:space:]]*BILLO_DOMAIN[[:space:]]*=[[:space:]]*//p' "$ROOT/.env" | tail -n 1 | tr -d '\r')"
  domain_pattern='^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$'
  if [[ ! "$billo_domain" =~ $domain_pattern ]]; then
    echo "BILLO_DOMAIN is not a safe DNS hostname for the system Caddy configuration." >&2
    exit 1
  fi
  host_caddy_candidate="$(mktemp /etc/caddy/.Caddyfile.billo.XXXXXX)"
  sed "s/__BILLO_DOMAIN__/$billo_domain/g" "$HOST_CADDY_TEMPLATE" > "$host_caddy_candidate"
  chmod 0644 "$host_caddy_candidate"
  if grep -q '__BILLO_DOMAIN__' "$host_caddy_candidate"; then
    echo "Host Caddy template rendering left an unresolved domain placeholder." >&2
    exit 1
  fi
  caddy validate --config "$host_caddy_candidate" --adapter caddyfile
fi

"${compose[@]}" build --pull
if [[ "$proxy_mode" == "docker" ]]; then
  "${compose[@]}" pull caddy
  "${compose[@]}" run --rm --no-deps caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
fi
# Stop every producer and consumer of correlated background work before the
# additive schema migration and service cutover. This prevents an old worker
# from mutating Core while a new Coordinator is enforcing the new protocol.
"${compose[@]}" stop -t 30 coordinator bill-auditor settlement-router imessage-gateway photon
"${compose[@]}" run --rm core python backend/scripts/apply_schema.py
"${compose[@]}" up -d --remove-orphans --wait --wait-timeout 180
"${compose[@]}" ps

if [[ "$proxy_mode" == "docker" && -z "$("${compose[@]}" ps --status running -q caddy)" ]]; then
  echo "Docker Caddy did not start; inspect its logs before sending traffic." >&2
  exit 1
fi

if [[ "$proxy_mode" == "host" ]]; then
  if cmp -s "$host_caddy_candidate" "$HOST_CADDY_CONFIG"; then
    echo "System Caddy configuration is already current."
  else
    backup="$HOST_CADDY_CONFIG.billo-backup.$(date -u +%Y%m%dT%H%M%SZ)"
    cp --preserve=mode,ownership,timestamps -- "$HOST_CADDY_CONFIG" "$backup"
    # The candidate is on the same filesystem, so rename makes the replacement
    # atomic. It was validated before any running configuration was changed.
    mv -f -- "$host_caddy_candidate" "$HOST_CADDY_CONFIG"
    host_caddy_candidate=""
    if ! systemctl reload caddy || ! systemctl is-active --quiet caddy; then
      echo "System Caddy rejected the new configuration; restoring $backup." >&2
      rollback_candidate="$(mktemp /etc/caddy/.Caddyfile.rollback.XXXXXX)"
      cp --preserve=mode,ownership,timestamps -- "$backup" "$rollback_candidate"
      mv -f -- "$rollback_candidate" "$HOST_CADDY_CONFIG"
      if caddy validate --config "$HOST_CADDY_CONFIG" --adapter caddyfile \
          && systemctl reload caddy \
          && systemctl is-active --quiet caddy; then
        echo "System Caddy rollback completed." >&2
      else
        echo "System Caddy rollback was restored on disk but could not be reloaded; operator action is required." >&2
      fi
      exit 1
    fi
    echo "System Caddy reloaded; previous configuration saved at $backup."
  fi
fi

echo "Billo is starting behind the $proxy_mode HTTPS gateway. Run deploy/oracle/smoke-test.py after DNS resolves."
