# Oracle Always Free deployment

This deployment keeps the Billo backend running continuously on one Oracle Ampere A1 VM. The Next.js frontend remains on Vercel and reaches the backend through HTTPS.

## Oracle VM

Create an Ubuntu 24.04 Ampere A1 instance in the account's home region. Stay inside the Always Free allowance, assign a public IPv4 address, paste `cloud-init.yaml` into the instance initialization script field, and add the user's SSH public key.

Open inbound TCP 22, 80 and 443 in the Oracle network security list. Open UDP 443 for HTTP/3. The cloud-init configuration applies the matching host firewall rules. Docker Caddy is the only public application ingress; Core and the agents stay on the private Compose network. Never expose ports 3000 or 8000–8007 publicly.

## DNS

Create an `A` record such as `api.heybillo.tech` pointing to the VM's reserved public IP. Set `BILLO_DOMAIN=api.heybillo.tech` and `PUBLIC_BASE_URL=https://api.heybillo.tech` in `.env`; the hostname in both values must match. Wait for the record to resolve to the VM before the production smoke test. Caddy uses `BILLO_DOMAIN` for certificate issuance and proxies requests to `core:8000` over the private Docker network.

## Start

Clone the repository into `/opt/billo`, create `/opt/billo/.env` from `.env.example`, and populate the production secrets. Then run:

```sh
cd /opt/billo
deploy/oracle/install.sh
deploy/oracle/smoke-test.py
```

Caddy obtains and renews the TLS certificate automatically. Every service restarts after a process failure or VM reboot.

`install.sh` starts Docker Caddy by default. For compatibility, it detects an already-running system Caddy service on older Billo hosts and keeps using that service with Core bound only to `127.0.0.1:8000`. To make the choice explicit, run `BILLO_PROXY_MODE=docker deploy/oracle/install.sh` for the canonical setup. An existing system-Caddy host must run `sudo env BILLO_PROXY_MODE=host deploy/oracle/install.sh` so the installer can render `Caddyfile.host`, validate it, atomically install it, and reload Caddy. The previous `/etc/caddy/Caddyfile` is timestamped before replacement and restored automatically if reload fails. The installer refuses conflicting, unprivileged, or unexpected host configurations instead of risking a port collision or replacing an unrelated Caddy file.

## Frontend

Set these Vercel Production environment variables and redeploy:

```text
CORE_URL=https://api.heybillo.tech
INTERNAL_TOKEN=<the same strong value used by the backend>
```

## Operations

```sh
docker compose -f deploy/oracle/compose.yml logs -f --tail=100 caddy core
docker compose -f deploy/oracle/compose.yml pull
docker compose -f deploy/oracle/compose.yml up -d --build
```

On an older system-Caddy host, include `-f deploy/oracle/compose.host-proxy.yml` in each Compose command. Do not use that override on new installations. Use `install.sh` for releases so the checked-in security headers and loopback upstream are safely reconciled into the system Caddy service.

Keep `.env` only on the VM and in the hosting dashboards. Never commit it.
