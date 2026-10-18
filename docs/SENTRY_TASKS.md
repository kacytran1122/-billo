# Sentry production tasks

Billo's code already emits privacy-safe traces, metrics, profiles, releases, Cron check-ins, and signed recovery alerts. Complete these one-time Sentry project tasks after the production DSN is installed.

## 1. Project and release health

- Set `SENTRY_ENVIRONMENT=production` and `SENTRY_RELEASE` to the deployed Git SHA.
- Confirm `/health` reports `observability.enabled: true` and the expected release without exposing the DSN.
- Create a release-health view grouped by `release` and `agent`.

## 2. Performance dashboard

Add widgets for:

- p50 and p95 span duration grouped by `task`.
- `billo.task.slow` grouped by `task` and `budget`.
- `billo.reader.path` grouped by `reader`.
- `billo.case.stage` grouped by `stage` and `channel`.
- `billo.settlement.result` grouped by `action`, `result`, and `mode`.
- `billo.medic.alert`, `billo.medic.applied`, and `billo.medic.duplicate` grouped by `action`.

## 3. Detectors and alerts

Create alerts that call the Internal Integration webhook at `https://<core>/sentry/webhook`:

- Document-reader failure rate is above 5% for 10 minutes.
- p95 document-reader duration exceeds 10 seconds for 10 minutes.
- Settlement guard has any unhandled error.
- Bridge delivery has three failures in five minutes.
- The `visit-followup` Cron monitor is missed or times out.
- A new regression appears in the production environment.

Route each alert with its controlled `check` tag: `bill_reader`, `npi`, `settlement`, `delivery`, `followup`, or `workflow`. Case Medic uses only these tags and never reads patient content.

## 4. Recovery smoke test

1. Put the Internal Integration Client Secret in `SENTRY_WEBHOOK_SECRET`.
2. Call `POST /demo/break-npi` with the internal token and a demo case ID.
3. Confirm one trace contains Core → signed webhook → Case Medic → Coordinator.
4. Deliver the same Sentry issue twice and confirm the second result is `already handled`.
5. Confirm no raw case ID, bill text, phone, email, amount, request body, or query string appears in the event.

## 5. Privacy and deployment gate

Run before every release:

```bash
make test
cd bridge && npm run typecheck
```

`tests/backend/test_sentry.py` inspects the exact outbound envelopes. A release is blocked if those tests find health data or identity fields.
