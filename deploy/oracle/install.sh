#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="$ROOT/deploy/oracle/compose.yml"

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

cd "$ROOT"
python3 deploy/check-production.py
docker compose -f "$COMPOSE" build --pull
docker compose -f "$COMPOSE" up -d --remove-orphans
docker compose -f "$COMPOSE" ps

echo "Billo is starting. Run deploy/oracle/smoke-test.py after DNS resolves."
