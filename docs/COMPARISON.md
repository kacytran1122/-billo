# Product and sponsor comparison

## Product boundary

Billo is intentionally not positioned as a generic medical-bill auditor, negotiator or dispute generator.

| Medical-bill audit products | Billo |
|---|---|
| Begin after a patient receives a suspicious bill | Begins before care and continues afterward |
| Detect duplicates, coding errors and high prices | Connects provider choice, estimate, visit log, final document and follow-up |
| Estimate savings | Creates a verified care record |
| Prepare disputes or negotiate balances | Routes paid receipts, unpaid bills and existing benefit sources |
| Primary outcome: reduce the charge | Primary outcome: safely complete and organize the care transaction |

The old two-check audit and dispute-letter workflow remains only as legacy internal code/tests during migration. It is not part of the user-facing primary workflow, demo or product claim.

## Sponsor roles

| Track | Distinct contribution |
|---|---|
| Fetch.ai | One ASI:One conversation coordinates specialist agents with typed messages |
| Photon | The same private workflow in iMessage, plus proactive visit follow-up |
| Visa | Guarded simulations for a verified clinic QR and an approved reimbursement; no real funds move |
| Tiger Data | Price context, estimate history, visit timeline and after-care records |
| Sentry | Privacy-safe distributed trace, cron monitoring and agent-driven recovery |

## Demo priorities

1. Complete the full journey in ASI:One.
2. Show a paid receipt being organized without creating a second charge.
3. Name a real benefit and show the **possible, not confirmed** response.
4. Show an unpaid bill reaching QR verification, explicit approval and a simulated Visa wallet handoff.
5. Show a paid receipt plus named benefit reaching an externally approved simulated reimbursement.
6. Show Photon carrying the same private workflow.
7. Trigger a Sentry failure and show Case Medic recover safely.

## Honest claims

- Receipt OCR and reconciliation are implemented.
- Benefit routing is deterministic, but eligibility and submission are not automated.
- Visa QR and reimbursement controls are implemented as an explicit simulation; no sandbox/API or real money movement is claimed.
- Real integrations require configured accounts, public endpoints and device testing.
