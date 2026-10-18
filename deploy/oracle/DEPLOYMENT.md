# Oracle Always Free deployment

This deployment keeps the Billo backend running continuously on one Oracle Ampere A1 VM. The Next.js frontend remains on Vercel and reaches the backend through HTTPS.

## Oracle VM

Create an Ubuntu 24.04 Ampere A1 instance in the account's home region. Stay inside the Always Free allowance, assign a public IPv4 address, paste `cloud-init.yaml` into the instance initialization script field, and add the user's SSH public key.

Open inbound TCP 22, 80 and 443 in the host firewall. Open UDP 443 for HTTP/3. The system Caddy service proxies to Core on loopback port 8000; never expose ports 3000 or 8000–8007 publicly. The Compose `docker-gateway` profile is only for hosts that do not already run Caddy.

## DNS

Create an `A` record such as `api.heybillo.tech` pointing to the VM's reserved public IP. Set `BILLO_DOMAIN=api.heybillo.tech` and `PUBLIC_BASE_URL=https://api.heybillo.tech` in `.env`.

## Start

Clone the repository into `/opt/billo`, create `/opt/billo/.env` from `.env.example`, and populate the production secrets. Then run:

```sh
cd /opt/billo
deploy/oracle/install.sh
deploy/oracle/smoke-test.py
```

Caddy obtains and renews the TLS certificate automatically. Every service restarts after a process failure or VM reboot.

## Frontend

Set these Vercel Production environment variables and redeploy:

```text
CORE_URL=https://api.heybillo.tech
INTERNAL_TOKEN=<the same strong value used by the backend>
```

## Operations

```sh
docker compose -f deploy/oracle/compose.yml logs -f --tail=100
docker compose -f deploy/oracle/compose.yml pull
docker compose -f deploy/oracle/compose.yml up -d --build
```

Keep `.env` only on the VM and in the hosting dashboards. Never commit it.
