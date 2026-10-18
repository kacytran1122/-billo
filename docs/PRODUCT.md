# Billo Product Design

## Product promise

> Plan the care. Organize what comes next.

Billo connects the decision made before care with the payment, records, benefits and follow-up after care. It is not a generic medical-bill auditing or dispute product.

## The problem

Healthcare is fragmented across search, booking, estimates, provider documents, payments, benefit programs and follow-up instructions. A patient must remember what was expected before the visit and reconcile it with multiple documents afterward. Existing bill-audit products focus primarily on detecting overcharges and negotiating disputes. Billo instead maintains continuity across the whole care transaction.

## Primary journey

```text
Before care
symptoms → emergency rules → nearby care → price comparison
→ booking → saved estimate → visit log

After care
receipt or final bill → OCR → verified care record
→ payment state → benefit paths → follow-up actions
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
4. Billo branches on payment state:
   - **Paid receipt:** create the care record and never create another charge.
   - **Unpaid final bill:** allow checkout only when the provider matches and the patient explicitly approves the exact amount.
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
| Payment Guard | Checks provider, destination, exact amount and signed limit |
| iMessage Gateway | Thin Photon adapter |
| Case Medic | Uses Sentry alerts to retry, degrade safely or pause payment |

The After-Care Organizer retains the historical source filename `agents/bill_auditor.py` and `SEED_BILL_AUDITOR` configuration key. Keeping the seed preserves its Agentverse address while the published name and behavior change.

## Typed workflow

```mermaid
sequenceDiagram
    participant U as Patient
    participant C as Coordinator
    participant O as After-Care Organizer
    participant T as Tiger Data
    participant G as Payment Guard
    participant V as Visa

    U->>C: paid receipt or unpaid final bill
    C->>O: AfterCareRequest
    O->>O: OCR or verified vision fallback
    O->>T: match estimate and visit log
    O-->>C: AfterCareResult
    alt already paid
        C-->>U: verified record; no payment
        U->>C: names an existing benefit
        C-->>U: possible path + documents + deadline warning
    else unpaid
        C-->>U: exact payment review
        U->>C: explicit approval
        C->>G: PayRequest
        G->>G: verify NPI, destination, amount and limit
        G->>V: create hosted checkout
        V-->>C: payment confirmation
        C-->>U: record updated
    end
```

## Sponsor integrations

### Fetch.ai

The complete journey runs inside one ASI:One conversation using Agent Chat Protocol and typed messages. The Coordinator demonstrates multi-agent orchestration rather than presenting a custom web frontend as the primary experience.

### Photon Spectrum

Photon provides the iMessage door. Private chats support booking, receipt upload, benefit checks and payment. Group chats respond only to `@Billo` and only with general before-care information. Sensitive after-care material never enters a group.

### Visa

Visa is used only for an unpaid final bill. Payment Guard verifies the provider, payment destination, exact amount and patient limit before checkout. Paid receipts bypass Visa. Card details are collected only on the hosted checkout page.

### Tiger Data

Tiger Data stores price history, estimates, visit events and after-care records. The visit log gives the organizer a timeline to match against the final document. An in-memory fallback keeps the demo runnable without a database.

### Sentry

Sentry records one privacy-safe trace across the case. It monitors OCR, benefit routing, provider verification, reminders and Visa. Case Medic can retry document reading, continue with a clearly labeled unverified provider state, or pause payments.

## Trust rules

1. Emergency screening runs first.
2. Code controls decisions; AI only reads documents and phrases messages.
3. A paid receipt cannot trigger payment.
4. Provider mismatch pauses payment.
5. Benefit eligibility is never inferred from a receipt.
6. Silence never moves money.
7. The patient explicitly approves the exact provider and amount.
8. Card numbers never enter Billo.
9. Uploaded documents are deleted after extraction.
10. Health data and raw phone numbers do not enter logs or Sentry.

## Demo story

Maya hurts her knee and asks Billo for affordable care near UCLA. The Red-Flag Screener clears emergency signs, Care Finder presents three options, and Maya books one. Billo saves the estimate and records that an X-ray occurred during the visit.

Maya later uploads a paid receipt. After-Care Organizer reads it, matches the provider and visit record, and confirms that no payment is needed. Maya says she has an HSA and out-of-network PPO. Billo shows two possible paths, lists the required documents and clearly states that eligibility depends on those plans.

For the alternative unpaid demo, Maya sends a final bill. Payment Guard verifies the provider and amount, Maya explicitly approves, and Visa returns a hosted checkout link.

## Competitive distinction

| Generic bill auditor | Billo |
|---|---|
| Starts with a suspicious bill | Can start before care |
| Finds coding errors or overcharges | Maintains continuity from estimate through follow-up |
| Measures possible savings | Organizes payment state, documents, benefits and next actions |
| Generates disputes or negotiations | Routes paid and unpaid documents safely |
| Core outcome is a lower bill | Core outcome is a completed and organized care transaction |

## Current implementation status

- Fetch.ai agents and typed messages: implemented
- Before-care emergency and care-finder flow: implemented
- Visit log and estimate matching: implemented
- OCR-first document reader: implemented
- After-care record and benefit routing: implemented
- Paid-receipt payment block: implemented
- Photon bridge: implemented; requires configured Spectrum account and real-device testing
- Sentry tracing and Case Medic: implemented; alert rule/webhook configuration required
- Tiger Data: supported; schema migration included
- Visa: mock checkout implemented; real sandbox checkout and webhook signature verification remain
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
- Real Visa sandbox checkout is not yet implemented.
- Demo care locations and prices remain synthetic until real sources are loaded.
