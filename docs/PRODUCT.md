# Billo Product Design

## Product promise

> Make every care dollar count.

Billo connects the decision made before care with the records, benefits, guarded settlement simulation and follow-up after care. It is not a generic medical-bill auditing or dispute product.

## The problem

Healthcare is fragmented across search, booking, estimates, provider documents, benefit programs and follow-up instructions. A patient must remember what was expected before the visit and reconcile it with multiple documents afterward. Existing bill-audit products focus primarily on detecting overcharges and negotiating disputes. Billo instead maintains continuity across the whole care journey.

## Primary journey

```text
Before care
symptoms → emergency rules → nearby care → price comparison
→ booking → saved estimate → visit log

After care
receipt or final bill → OCR → verified care record
→ payment status → guarded Visa simulation or benefit path → follow-up actions
```

### Before care

1. Fixed rules check emergency warning signs. An emergency stops the shopping workflow and tells the patient to call 911.
2. Care Finder shows nearby options, hours and price context.
3. The patient chooses a provider.
4. Billo saves a Good Faith Estimate and calendar event.
5. During the visit, the patient can record services in plain language to maintain an expected-cost timeline.

### After care

1. The patient sends a paid receipt or unpaid final bill in a private ASI:One or iMessage conversation.
2. The OCR-first reader extracts typed line items. Production rejects unreadable documents instead of inserting demo data.
3. After-Care Organizer matches the provider, total, estimate and visit log.
4. Billo branches on the verified document state:
   - **Paid receipt:** create the care record, preserve proof of payment, and never create a second clinic charge.
   - **Unpaid final bill:** verify a clinic-presented Visa QR against provider, exact amount, currency, invoice, network and checksum, then require explicit approval for a simulated wallet handoff.
     After a named benefit and external approval, require explicit approval for a simulated Visa Direct reimbursement.
5. Billo asks about benefits only as an optional branch. It never assumes reimbursement.
6. The record remains the basis for follow-up care, future cost planning and document organization.

## Benefits policy

A receipt alone does not create a reimbursement right. Billo shows a possible path only when the patient says they have one of these sources:

- HSA, FSA or HRA
- out-of-network insurance coverage
- employer health benefit
- university or student health benefit
- travel insurance
- accident insurance

Every path is labeled **possible, not confirmed**. Billo lists the likely documents and tells the patient to check the plan rules and deadline. Automatic claim submission, eligibility promises and tax advice are out of scope.

## Agent system

| Agent | Work |
|---|---|
| Coordinator | One front door in ASI:One; owns state and routes every step |
| Red-Flag Screener | Fixed emergency rules |
| Care Finder | Care options and price context |
| After-Care Organizer | Reads and reconciles the receipt/final bill |
| Care Settlement Router | Guards the two Visa simulation directions |
| iMessage Gateway | Thin Photon adapter |
| Case Medic | Uses Sentry alerts to retry or preserve a record for review |

The After-Care Organizer retains the historical source filename `backend/fetch.ai/bill_auditor.py` and `SEED_BILL_AUDITOR` configuration key. Keeping the seed preserves its Agentverse address while the published name and behavior change.

## Typed workflow

```mermaid
sequenceDiagram
    participant U as Patient
    participant C as Coordinator
    participant O as After-Care Organizer
    participant T as Tiger Data
    participant S as Care Settlement Router

    U->>C: paid receipt or unpaid final bill
    C->>O: AfterCareRequest
    O->>O: OCR or verified vision fallback
    O->>T: match estimate and visit log
    O-->>C: AfterCareResult
    alt already paid
        C-->>U: verified paid record; no second charge
        U->>C: names an existing benefit
        C-->>U: possible path + documents + deadline warning
        U->>C: external approval + explicit demo approval
        C->>S: simulate Visa Direct reimbursement
        S-->>U: simulated payout record; no funds moved
    else unpaid
        U->>C: clinic Visa QR
        C->>S: verify QR and saved bill
        S-->>U: exact merchant and amount review
        U->>C: explicit approval
        S-->>U: simulated wallet handoff; no funds moved
    end
```

## Sponsor integrations

### Fetch.ai

The complete journey runs inside one ASI:One conversation using Agent Chat Protocol and typed messages. The Coordinator demonstrates multi-agent orchestration rather than presenting a custom web frontend as the primary experience.

### Photon Spectrum

Photon provides the iMessage door. Every private or group request must visibly tag `@Billo`; untagged content is ignored, except that private `STOP` always opts out. Private chats support booking, receipt upload and benefit checks. Group chats return only general before-care information. Sensitive after-care material never enters a group.

### Visa

Visa settlement is deliberately simulated because this project does not have access to a Visa sandbox or money APIs. The active flow still demonstrates code-enforced QR verification, payment-state separation, external benefit approval, explicit consent, idempotency and audit records. It never collects card data or claims that money moved.

### Tiger Data

Tiger Data stores price history, estimates, visit events and after-care records. The visit log gives the organizer a timeline to match against the final document. An in-memory fallback keeps the demo runnable without a database.

### Sentry

Sentry records one privacy-safe trace across the case. It monitors OCR, benefit routing, reconciliation and reminders. Case Medic can retry document reading or preserve a record for review.

## Trust rules

1. Emergency screening runs first.
2. Code controls decisions; AI only reads documents and phrases messages.
3. Every Visa result says simulation/no money moved.
4. Paid receipts cannot enter clinic payment; unpaid bills cannot enter reimbursement.
5. Benefit eligibility is never inferred from a receipt.
6. Billo never requests card numbers and never treats silence as approval.
7. Uploaded documents are deleted after extraction.
8. Health data and raw phone numbers do not enter logs or Sentry.

## Demo story

Maya hurts her knee and asks Billo for affordable care near UCLA. The Red-Flag Screener clears emergency signs, Care Finder presents three options, and Maya books one. Billo saves the estimate and records that an X-ray occurred during the visit.

Maya later uploads a paid receipt. After-Care Organizer reads it, matches the provider and visit record, and confirms that no payment is needed. Maya says she has an HSA and out-of-network PPO. Billo shows two possible paths, lists the required documents and clearly states that eligibility depends on those plans.

For the alternative unpaid demo, Maya sends a final bill and the clinic's Visa QR. Billo validates the QR against the saved provider and exact bill, asks for explicit approval, and produces a simulated wallet handoff that states no money moved.

## Competitive distinction

| Generic bill auditor | Billo |
|---|---|
| Starts with a suspicious bill | Can start before care |
| Finds coding errors or overcharges | Maintains continuity from estimate through follow-up |
| Measures possible savings | Organizes document status, benefits and next actions |
| Generates disputes or negotiations | Routes paid and unpaid documents safely |
| Core outcome is a lower bill | Core outcome is a completed and organized care transaction |

## Current implementation status

- Fetch.ai agents and typed messages: implemented
- Before-care emergency and care-finder flow: implemented
- Visit log and estimate matching: implemented
- OCR-first document reader: implemented
- After-care record and benefit routing: implemented
- Paid/unpaid/unknown document status: implemented
- Clinic Visa QR validation and explicit-approval simulation: implemented
- Benefit-approved Visa Direct reimbursement simulation: implemented
- Photon bridge: implemented; requires configured Spectrum account and real-device testing
- Sentry tracing and Case Medic: implemented; alert rule/webhook configuration required
- Tiger Data: supported; schema migration included
- NPI: demo by default; live registry mode supported

## Demo language

Use:

> Billo helps patients plan affordable care before a visit and organize everything afterward. It turns a receipt or final bill into a verified care record, coordinates follow-up and checks possible benefit paths without promising eligibility.

Do not describe Billo as finding billing mistakes, calculating savings, disputing unfair charges or paying only the fair portion. Those are not the new primary product.

## Limitations

- Billo does not determine medical necessity.
- Billo does not guarantee insurance or benefit eligibility.
- Billo does not submit claims in the current build.
- Billo does not provide legal, tax, medical or financial advice.
- Visa settlement is simulated; no real funds move and no card data is collected.
- Demo care locations and prices remain synthetic until real sources are loaded.
