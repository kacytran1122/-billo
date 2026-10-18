# Billo

[![CI](https://github.com/kacytran1122/-billo/actions/workflows/ci.yml/badge.svg)](https://github.com/kacytran1122/-billo/actions/workflows/ci.yml)

[![Billo system architecture](docs/architecture.png)](docs/architecture.svg)

The diagram is available as an editable SVG. Select the image to open it at full resolution.

**Make every care dollar count.**

Billo is an AI care companion that helps patients understand costs before care and organize bills, receipts, benefits, and next steps afterward. It works in ASI:One and in tagged iMessage conversations through Photon Spectrum, with deterministic safety and payment rules around every AI-assisted action.

Built for **LA Hacks 2026** at UCLA.

> Every patient, provider, document, and payment shown in the demo is synthetic. Billo does not provide medical, legal, insurance, tax, or financial advice. In an emergency, call 911.

## Why Billo exists

Patients are often asked to make expensive healthcare decisions before they know the price, then decode unfamiliar bills and reimbursement rules after the visit. The useful information exists, but it is scattered across price files, provider records, receipts, benefit documents, and payment portals.

Billo keeps those steps connected. Before care, it screens for emergency signs, compares nearby options, records an estimate, and follows the visit. After care, it reads the final bill or paid receipt, matches it to the visit, explains what changed, and identifies possible benefit or reimbursement paths only when the patient names a real benefit.

## Tracks

| Track | How Billo fits |
| --- | --- |
| **Fetch.ai / ASI:One** | A coordinator routes each case through specialist agents for safety screening, care search, document organization, settlement checks, and recovery. |
| **Photon** | Billo joins private or group iMessage chats through Spectrum and responds only when a user explicitly tags `@Billo`. |
| **TigerData** | Stores price history, visit events, document results, and after-care records for fast retrieval and comparison. |
| **Sentry** | Traces one case across the bridge, agents, OCR, API, and database, then wakes Case Medic when a monitored workflow fails. |
| **Visa** | Demonstrates guarded clinic-QR payment and reimbursement flows as simulations; no card data is collected and no money moves. |

## What it does

Before a visit, a patient can describe what happened in plain language. Billo applies fixed emergency rules first, then returns nearby care options and estimated prices, records the selected visit, and maintains a running expected total.

After the visit, the patient can upload a final bill or paid receipt. Local OCR reads the document first, a vision model assists only when confidence is low, and deterministic checks match the provider, line items, amount, and saved estimate. Billo then organizes follow-up documents and possible HSA, FSA, HRA, insurance, employer, school, travel, or accident-benefit paths.

An unpaid clinic bill can enter a simulated Visa QR flow only after the clinic, invoice, currency, and exact amount match. A paid receipt can enter a simulated reimbursement flow only after an external benefit approval. Both paths require explicit patient approval and are visibly labeled as simulations.

## End-to-end example

One case stays connected across the entire experience instead of becoming a collection of unrelated searches and uploads.

| Stage | Patient action | Billo action | Durable result |
| --- | --- | --- | --- |
| Safety | Describes symptoms in ASI:One or tags `@Billo` in iMessage | Applies fixed emergency rules before any shopping | Safety result and case identifier |
| Search | Gives a need and location | Returns up to three care options with comparable prices | Selected provider and source metadata |
| Estimate | Chooses an option | Saves the expected price and produces calendar links | Good Faith Estimate and visit record |
| During care | Reports a service such as an X-ray | Adds the service to the running visit log | Updated expected total |
| Document | Uploads a final bill or paid receipt | Extracts fields, verifies OCR, and matches provider, amount, and visit | Structured after-care record |
| Route | Names a real benefit or scans a clinic QR | Selects the paid-benefit or unpaid-clinic path | Review with mismatches and required evidence |
| Approval | Explicitly approves the demonstrated action | Rechecks every guard and writes an idempotent simulation record | Auditable outcome; no real money movement |

## Chat commands

```text
@Billo                                      show the command menu
@Billo my knee hurts near UCLA              screen safety and compare care
@Billo book 1                               save the selected visit and estimate
@Billo they did an X-ray                    update the live visit log
@Billo here is my final bill                read and organize an unpaid bill
@Billo here is my paid receipt              read and organize a paid receipt
@Billo I have an HSA                        check possible benefit paths
@Billo status                               show the current case and next action
STOP                                        cancel queued reminders
```

Billo stays quiet unless it is tagged, so ordinary conversation is never forwarded. Untagged `STOP` is the sole exception so opting out cannot be blocked.

## Architecture

The diagram follows a request from ASI:One or iMessage into the coordinator, through the specialist Fetch.ai agents, and into shared FastAPI tools for rules, OCR, storage, and drafting. TigerData holds durable case state, Sentry observes the workflow without receiving raw health data, and the Visa boundary remains a clearly labeled simulation.

Arrow direction is intentional: solid navy arrows carry requests or application data toward the next owner; dashed pink arrows carry scrubbed telemetry into Sentry; the solid pink arrow carries a signed recovery alert out of Sentry to Case Medic. Monitoring and recovery are shown separately so an alert can never be mistaken for a patient or payment request.

```text
Patient
  ├─ ASI:One ───────────────┐
  └─ iMessage + Photon ─────┤
                            ▼
                    Billo Coordinator
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
   Safety + Care      After-Care OCR     Settlement Guard
          └─────────────────┼─────────────────┘
                            ▼
                  FastAPI + TigerData
                     │             │
                  Sentry      Visa simulation
```

### Agent responsibilities

| Agent | Input | Responsibility | Output |
| --- | --- | --- | --- |
| Billo Coordinator | Patient message and current case | Maintains the conversation state and selects one specialist | Typed task or patient-facing response |
| Red-Flag Screener | Symptoms and context | Applies non-LLM emergency rules first | Stop-and-seek-help result or cleared state |
| Care Finder | Need, location, and payment context | Calls care and price tools and formats comparable choices | Sourced care options |
| After-Care Organizer | Bill or receipt extraction | Reconciles provider, amount, line items, estimate, and visit log | Structured after-care record and mismatches |
| Settlement Router | Verified record and explicit approval | Enforces provider, amount, status, consent, and idempotency | Simulated QR handoff or reimbursement result |
| iMessage Gateway | Sanitized Photon event | Translates transport events into typed agent messages | Coordinator request or safe rejection |
| Case Medic | Signed Sentry issue payload | Chooses one bounded recovery action and deduplicates delivery | Recovery record and operator notice |

### Core API surface

The agents share one FastAPI service instead of duplicating safety logic. Important routes include:

| Route | Purpose |
| --- | --- |
| `GET /health` | Reports release, environment, Sentry state, and service readiness without exposing secrets |
| `GET /care/search` | Returns normalized care options and prices |
| `POST /estimates` | Saves the selected provider and expected amount |
| `POST /visit-events` | Adds services to the live visit log |
| `POST /reader/extract` | Runs OCR-first extraction with guarded vision fallback |
| `POST /after-care/organize` | Reconciles a document against provider, visit, and estimate evidence |
| `POST /benefits/check` | Returns conditional benefit paths from benefits the patient actually names |
| `POST /visa/qr/inspect` | Validates simulated clinic QR fields before approval is possible |
| `POST /visa/qr/approve` | Rechecks an unpaid-bill simulation and records explicit consent |
| `POST /visa/reimbursement/payout` | Records an approved paid-receipt reimbursement simulation |
| `POST /sentry/webhook` | Accepts signed Sentry alerts and dispatches deduplicated Case Medic work |

## Why the AI cannot bypass the rules

The language model reads documents and phrases responses, but it does not decide whether an emergency flow stops, a bill matches, or a payment can continue. Those decisions live in deterministic code. A paid receipt cannot enter the clinic-payment branch, provider or amount mismatches block approval, repeated requests are idempotent, and silence never counts as consent.

Sentry receives a keyed case hash rather than a patient identity. Request bodies, query strings, model inputs and outputs, SQL parameters, uploaded documents, phone numbers, emails, dates, card-like numbers, and amounts are scrubbed before telemetry leaves the application.

The document pipeline also has a fixed trust order:

1. Validate file size and media type.
2. Run local RapidOCR.
3. Use the configured vision model only when OCR confidence or line count is insufficient.
4. Compare model fields against OCR evidence rather than trusting them directly.
5. Normalize codes and amounts into the structured record.
6. Delete the temporary upload after extraction.

## Case state and persistence

TigerData stores the minimum state needed to reconnect the workflow: hashed case identity, care options, saved estimate, visit events, extracted document fields, reconciliation status, benefit checks, and settlement-simulation audit records. Raw uploaded documents are not treated as durable case storage.

When `DATABASE_URL` is absent, local development uses the in-memory fallback. Production readiness checks require the database so restarts do not erase a case. Link codes bind an ASI:One case to iMessage without putting a patient identifier in the QR payload.

## Sentry observability and recovery

One patient case maps to one distributed trace across Photon, the iMessage Gateway, the Coordinator, specialist agents, the Core API, and the reply. The implementation includes:

- latency spans and performance budgets for care search, OCR, reconciliation, bridge delivery, and settlement;
- metrics for case stages, OCR path, outcomes, and recovery actions;
- Sentry Crons for scheduled visit follow-up checks;
- release and environment diagnostics through `/health`;
- a signed webhook with replay-safe delivery deduplication;
- Case Medic recovery choices limited to known safe actions; and
- privacy tests that inspect outbound Sentry envelopes rather than only configuration values.

Expected user-facing guard failures remain normal application responses. They annotate the trace but do not create noisy operational incidents.

## Repository

```text
backend/
  api/             FastAPI rules, OCR endpoints, care search, and case tools
  fetch.ai/        coordinator and specialist agents
  photon/          Photon Spectrum bridge for iMessage
  ocr/             local OCR and vision-fallback verification
  observability/   Sentry tracing, privacy filters, metrics, and recovery
  database/        TigerData schema
  integrations/    archived and simulated provider integrations
frontend/          responsive Next.js product experience
deploy/oracle/     Oracle Ampere deployment, Caddy, checks, and smoke tests
tests/              backend, frontend, Photon, OCR, and deployment tests
docs/               architecture and product documentation
.github/workflows/  CI and ARM64 container validation
```

## Run locally

Requirements: Python 3.11+, Node.js 22+, `uv`, Docker, and Make.

```bash
git clone https://github.com/kacytran1122/-billo.git
cd -- -billo
make setup
make env
```

Fill `.env` locally. Never commit API keys, agent seeds, database credentials, certificates, or private keys.

Configuration is grouped by responsibility:

| Group | Important variables |
| --- | --- |
| Runtime | `BILLO_MODE`, `CORE_URL`, `PUBLIC_BASE_URL`, `INTERNAL_TOKEN` |
| Fetch.ai | `ASI_ONE_API_KEY`, permanent `SEED_*` values, derived `ADDR_*` values |
| Documents | `VISION_API_KEY`, `VISION_MODEL`, `OCR_MIN_CONFIDENCE`, `OCR_MAX_IMAGE_BYTES` |
| Persistence | `DATABASE_URL` |
| Photon | `SPECTRUM_PROJECT_ID`, `SPECTRUM_PROJECT_SECRET`, `PHOTON_LINE_ADDRESS` |
| Sentry | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, `CASE_HASH_KEY`, `SENTRY_WEBHOOK_SECRET` |
| Simulation | `VISA_QR_MODE=simulate`, `VISA_DIRECT_MODE=simulate`, `NPI_MODE` |

```bash
make test       # backend, OCR, safety, and integration tests
make core       # Core API at http://localhost:8000/docs
make fetch-ai   # Fetch.ai agents
make bridge     # Photon bridge
```

Run the frontend separately:

```bash
cd frontend
npm ci
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

## Tests and verification

The CI workflow validates the application on every push:

| Suite | Coverage |
| --- | --- |
| Backend | API contracts, workflow guards, OCR, Sentry privacy, Oracle configuration, production readiness, and smoke-test behavior |
| Frontend | Responsive layouts, dedicated journey routes, startup loader, live simulation, formatting, and safe handoff construction |
| Photon | Tag activation, mention removal, ignored untagged messages, and group privacy routing |
| Build | Next.js production compilation and Photon TypeScript checks |
| Deployment | Core, Fetch.ai, and Photon Docker images built for Oracle's `linux/arm64` architecture |

The current verified baseline is 69 backend tests, 27 frontend tests, 4 Photon routing tests, a successful Next.js production build, and three successful ARM64 container builds.

## Production

The frontend is designed for Vercel. The long-running FastAPI, OCR, Fetch.ai, and Photon services deploy as ARM64 containers on an Oracle Ampere A1 VM behind Caddy.

```bash
cd deploy/oracle
./install.sh
python3 smoke-test.py https://api.heybillo.tech
```

Keep `BILLO_MODE=demo` during the first deployment. After HTTPS, database, Sentry webhook, OCR, and end-to-end smoke checks pass, switch to `BILLO_MODE=live` and perform one final tagged iMessage test with a sanitized document.

Recommended production sequence:

1. Create an Oracle Ampere A1 VM and allow inbound ports 22, 80, and 443.
2. Point `api.heybillo.tech` to the VM's public IP.
3. Place secrets directly in the server environment; never paste them into issues or commits.
4. Run `deploy/oracle/install.sh` to validate configuration, build containers, and start Caddy.
5. Run the HTTPS smoke test against the public domain.
6. Configure the signed Sentry webhook at `/sentry/webhook` and verify one recovery demo.
7. Set the Vercel backend URL to `https://api.heybillo.tech` and redeploy the frontend.
8. Switch to live mode only after a sanitized OCR test and a real tagged iMessage round trip pass.

## What is real and what is simulated

| Part | Status |
| --- | --- |
| Fetch.ai agents and Chat Protocol | Real |
| Emergency rules and after-care routing | Real deterministic code |
| OCR and vision fallback | Real; vision runs only when local OCR is uncertain |
| TigerData persistence | Real when `DATABASE_URL` is configured |
| Photon iMessage transport | Real when Spectrum credentials and a line are configured |
| Sentry tracing and recovery | Real after the signed webhook is configured |
| NPI registry lookup | Demo by default; live mode is available |
| Care prices | Synthetic until public price files are loaded |
| Visa payment and reimbursement | Deliberate simulation only |

## Safety notes

- Emergency indicators stop shopping and direct the patient to urgent help.
- Benefit results are possible paths, not eligibility decisions or guarantees.
- Uploaded documents are deleted after extraction.
- No PAN, CVV, or bank credential is collected.
- Every settlement result states that it is simulated.
- Every payment-like action requires explicit approval.

## License

MIT
