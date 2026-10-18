"""Visa payments. Two modes:

VISA_MODE=mock     -> a fake hosted pay page on PUBLIC_BASE_URL (/pay/<id>); "paying" it marks the payment done.
VISA_MODE=sandbox  -> Visa Acceptance (Cybersource) sandbox pay-by-link / invoice.  TODO(visa): fill in.

Rules that never change, whatever the mode:
- Billo never sees card numbers (Visa's hosted page collects the card).
- One idempotency key per (case, amount), so a retry never charges twice.
- Only an explicitly approved, verified final amount is sent here.
"""
from __future__ import annotations

import hashlib
import os
import time

from . import store

PUBLIC = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


def create_pay_link(case_id: str, amount: float) -> dict:
    key = hashlib.sha256(f"{case_id}:{amount:.2f}".encode()).hexdigest()[:16]  # idempotency key
    existing = store.get_payment(key)
    if existing:
        return existing
    mode = os.getenv("VISA_MODE", "mock")
    if mode == "sandbox":
        # TODO(visa): call the Visa Acceptance Agent Toolkit (invoices / pay-by-link) or Cybersource REST
        #   - create an invoice or payment link for `amount` USD with reference=case_id
        #   - pass `key` as the idempotency key
        #   - store the returned URL + id; the webhook /visa/webhook marks it paid
        raise NotImplementedError("Set VISA_MODE=mock until the sandbox call is filled in (see AGENTS.md, task V1).")
    rec = {"payment_id": key, "url": f"{PUBLIC}/pay/{key}", "amount": round(amount, 2), "case_id": case_id,
           "paid": False, "mode": "mock", "created_at": time.time()}
    store.save_payment(key, rec)
    return rec


def mark_paid(payment_id: str) -> dict | None:
    rec = store.get_payment(payment_id)
    if rec:
        rec["paid"] = True
        rec["paid_at"] = time.time()
    return rec
