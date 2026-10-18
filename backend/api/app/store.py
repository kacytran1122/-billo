"""Data access. Uses Tiger Data (Postgres + TimescaleDB) when DATABASE_URL is set,
otherwise an in-memory store + the synthetic CSV, so the demo always runs.
"""
from __future__ import annotations

import csv
import copy
import hashlib
import json
import os
import statistics
import threading
import time
import re
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SYN = BACKEND_ROOT / "data" / "synthetic"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

_mem: dict[str, dict] = {
    "estimates": {}, "visit_events": {}, "after_care": {}, "benefit_checks": {},
    "settlements": {}, "links": {}, "public_links": {}, "stopped": set(), "reminders": {},
    "operations": {},
}

OPERATION_KINDS = frozenset({"after_care", "settlement"})
OPERATION_TTL_SECONDS = 300
_OPERATION_RESULT_FIELDS = {
    "after_care": frozenset({
        "total", "hospital_npi", "payment_status", "provider_match",
        "estimate_amount", "estimate_difference", "visit_items_matched",
        "next_steps", "reader", "unreviewed_lines", "needs_review",
        "fallback_reason",
    }),
    "inspect_qr": frozenset({
        "status", "settlement_id", "trusted", "reasons", "merchant_name",
        "amount", "mode",
    }),
    "approve_qr": frozenset({
        "status", "settlement_id", "trusted", "reasons", "merchant_name",
        "amount", "mode",
    }),
    "reimburse": frozenset({
        "status", "settlement_id", "trusted", "reasons", "merchant_name",
        "amount", "mode",
    }),
}
_operation_locks: dict[str, threading.RLock] = {}
_operation_locks_guard = threading.Lock()

_schema_ready = False


def _conn():
    import psycopg  # imported lazily so the demo works without it
    return psycopg.connect(DATABASE_URL, autocommit=True)


def use_db() -> bool:
    return bool(DATABASE_URL) and "PASSWORD@HOST" not in DATABASE_URL


def _timestamp(value) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    return float(value)


def _ensure_runtime_schema(connection) -> None:
    """Apply small additive migrations needed by rolling deployments.

    `schema.sql` remains the source for fresh databases.  These idempotent DDL
    statements let an existing deployment accept the new public-link contract
    before a separate migration job has run.
    """
    global _schema_ready
    if _schema_ready:
        return
    connection.execute("ALTER TABLE estimates ADD COLUMN IF NOT EXISTS payload JSONB")
    connection.execute("ALTER TABLE settlements ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()")
    connection.execute("ALTER TABLE link_codes ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'imessage'")
    connection.execute("ALTER TABLE link_codes ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS public_access_tokens (
           token_hash TEXT PRIMARY KEY, scope TEXT NOT NULL, case_id TEXT NOT NULL,
           subject_id TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
           created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
           updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
           UNIQUE (scope, subject_id))"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS active_operations (
           case_id TEXT PRIMARY KEY, kind TEXT NOT NULL, request_id TEXT NOT NULL,
           status TEXT NOT NULL DEFAULT 'active', action TEXT NOT NULL DEFAULT '',
           result JSONB,
           updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
           CHECK (kind IN ('after_care', 'settlement')),
           CHECK (status IN ('active', 'completed')))"""
    )
    # Additive compatibility for the short-lived composite-key version. Keep
    # its primary key in place and add a case-wide unique index after retaining
    # only the newest row for each case.
    connection.execute("ALTER TABLE active_operations ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'")
    connection.execute("ALTER TABLE active_operations ADD COLUMN IF NOT EXISTS action TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE active_operations ADD COLUMN IF NOT EXISTS result JSONB")
    connection.execute(
        """DELETE FROM active_operations
           WHERE ctid IN (
             SELECT ctid FROM (
               SELECT ctid, row_number() OVER (
                 PARTITION BY case_id ORDER BY updated_at DESC, kind DESC
               ) AS duplicate_number
               FROM active_operations
             ) ranked
             WHERE duplicate_number > 1
           )"""
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS active_operations_case_unique ON active_operations (case_id)"
    )
    _schema_ready = True


# ---------------------------------------------------------------- asynchronous operation correlation
def _valid_operation(case_id: str, kind: str, request_id: str) -> bool:
    return bool(case_id and request_id and kind in OPERATION_KINDS)


class OperationInactive(RuntimeError):
    """The requested operation is missing, superseded, expired, or mismatched."""


def _operation_lock_key(case_id: str) -> int:
    digest = hashlib.sha256(case_id.encode()).digest()[:8]
    return int.from_bytes(digest, byteorder="big", signed=True)


@contextmanager
def _operation_lock(case_id: str):
    """Serialize every operation kind and guarded write for one case."""
    if use_db():
        with _conn() as connection:
            _ensure_runtime_schema(connection)
            lock_key = _operation_lock_key(case_id)
            connection.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
            try:
                yield connection
            finally:
                connection.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
        return
    with _operation_locks_guard:
        lock = _operation_locks.setdefault(case_id, threading.RLock())
    with lock:
        yield None


def _operation_locked(connection, case_id: str) -> dict | None:
    if connection is not None:
        row = connection.execute(
            """SELECT kind, request_id, status, action, result,
                      EXTRACT(EPOCH FROM updated_at)
               FROM active_operations WHERE case_id=%s""",
            (case_id,),
        ).fetchone()
        if not row:
            return None
        result = row[4] if isinstance(row[4], dict) or row[4] is None else json.loads(row[4])
        operation = {
            "kind": str(row[0]), "request_id": str(row[1]), "status": str(row[2]),
            "action": str(row[3] or ""), "result": result, "updated_at": float(row[5]),
        }
        _mem["operations"][case_id] = copy.deepcopy(operation)
        return operation
    operation = _mem["operations"].get(case_id)
    return copy.deepcopy(operation) if operation else None


def _operation_matches(operation: dict | None, kind: str, request_id: str) -> bool:
    return bool(
        operation
        and operation.get("kind") == kind
        and operation.get("request_id") == request_id
    )


def _operation_is_active(operation: dict | None, kind: str, request_id: str) -> bool:
    return bool(
        _operation_matches(operation, kind, request_id)
        and operation.get("status") == "active"
        and float(operation.get("updated_at", 0)) >= time.time() - OPERATION_TTL_SECONDS
    )


def _operation_is_completed(operation: dict | None, kind: str, request_id: str) -> bool:
    # Completion is durable truth, not a short-lived delivery cache. The row is
    # already sanitized and case-unique, and a new operation explicitly replaces
    # it, so aging it into "inactive" would make a committed write look uncommitted.
    return bool(
        _operation_matches(operation, kind, request_id)
        and operation.get("status") == "completed"
    )


def _cacheable_operation_result(action: str, result: dict) -> dict:
    """Retain only delivery fields, never bearer URLs or copied document rows."""
    allowed = _OPERATION_RESULT_FIELDS.get(action)
    if allowed is None or not isinstance(result, dict):
        raise ValueError("unsupported operation result")
    return {
        key: copy.deepcopy(result[key])
        for key in allowed
        if key in result
    }


def _cancel_operation_locked(connection, case_id: str, kind: str, request_id: str) -> bool:
    if connection is not None:
        cursor = connection.execute(
            """DELETE FROM active_operations
               WHERE case_id=%s AND kind=%s AND request_id=%s AND status='active'""",
            (case_id, kind, request_id),
        )
        deleted = cursor.rowcount == 1
    else:
        operation = _mem["operations"].get(case_id)
        deleted = bool(
            _operation_matches(operation, kind, request_id)
            and operation.get("status") == "active"
        )
    if deleted:
        _mem["operations"].pop(case_id, None)
    return deleted


def start_operation(case_id: str, kind: str, request_id: str) -> None:
    """Make request_id the only authorized mutation of any kind for this case."""
    if not _valid_operation(case_id, kind, request_id):
        raise ValueError("invalid operation")
    with _operation_lock(case_id) as connection:
        existing = _operation_locked(connection, case_id)
        # HTTP retries of the same logical start must not refresh an expired
        # grant or erase a completed replay result. A genuinely new operation
        # always carries a fresh request id.
        if _operation_matches(existing, kind, request_id):
            return
        now = time.time()
        operation = {
            "kind": kind, "request_id": request_id, "status": "active",
            "action": "", "result": None, "updated_at": now,
        }
        if connection is not None:
            connection.execute(
                """INSERT INTO active_operations
                     (case_id, kind, request_id, status, action, result, updated_at)
                   VALUES (%s,%s,%s,'active','',NULL,now())
                   ON CONFLICT (case_id) DO UPDATE SET
                     kind=EXCLUDED.kind, request_id=EXCLUDED.request_id,
                     status='active', action='', result=NULL, updated_at=now()""",
                (case_id, kind, request_id),
            )
        _mem["operations"][case_id] = operation


def operation_active(case_id: str, kind: str, request_id: str) -> bool:
    """Return true only for the current, unexpired operation identifier."""
    if not _valid_operation(case_id, kind, request_id):
        return False
    with _operation_lock(case_id) as connection:
        return _operation_is_active(_operation_locked(connection, case_id), kind, request_id)


def cancel_operation(case_id: str, kind: str, request_id: str) -> bool:
    """Remove an operation only when all three correlation fields still match."""
    if not _valid_operation(case_id, kind, request_id):
        return False
    with _operation_lock(case_id) as connection:
        return _cancel_operation_locked(connection, case_id, kind, request_id)


def operation_status(case_id: str, kind: str, request_id: str) -> dict:
    """Read status for an exact operation without exposing its identifiers."""
    if not _valid_operation(case_id, kind, request_id):
        return {"status": "inactive"}
    with _operation_lock(case_id) as connection:
        operation = _operation_locked(connection, case_id)
        if not _operation_matches(operation, kind, request_id):
            return {"status": "inactive"}
        if _operation_is_completed(operation, kind, request_id):
            return {
                "status": "completed", "action": operation.get("action", ""),
                "result": copy.deepcopy(operation.get("result")),
            }
        if _operation_is_active(operation, kind, request_id):
            return {"status": "active"}
        return {"status": "inactive"}


def run_operation(case_id: str, kind: str, request_id: str, action: str, callback):
    """Run or replay one mutation while holding the case-wide operation lock.

    A successful result is retained until the next operation starts. Callback
    exceptions leave the active grant intact for a bounded retry.
    """
    if not _valid_operation(case_id, kind, request_id) or action not in _OPERATION_RESULT_FIELDS:
        raise OperationInactive("operation is stale, expired, or inactive")
    with _operation_lock(case_id) as connection:
        operation = _operation_locked(connection, case_id)
        if _operation_is_completed(operation, kind, request_id):
            if operation.get("action") != action:
                raise OperationInactive("operation action does not match")
            return copy.deepcopy(operation.get("result"))
        if not _operation_is_active(operation, kind, request_id):
            raise OperationInactive("operation is stale, expired, or inactive")
        result = _cacheable_operation_result(action, callback())
        completed = {
            "kind": kind, "request_id": request_id, "status": "completed",
            "action": action, "result": copy.deepcopy(result), "updated_at": time.time(),
        }
        if connection is not None:
            connection.execute(
                """UPDATE active_operations
                   SET status='completed', action=%s, result=%s, updated_at=now()
                   WHERE case_id=%s AND kind=%s AND request_id=%s AND status='active'""",
                (action, json.dumps(result), case_id, kind, request_id),
            )
        _mem["operations"][case_id] = completed
        return copy.deepcopy(result)


# ---------------------------------------------------------------- prices
_csv_rows: list[dict] | None = None


def _rows() -> list[dict]:
    global _csv_rows
    if _csv_rows is None:
        with open(SYN / "prices.csv") as f:
            _csv_rows = [{**r, "price": float(r["price"])} for r in csv.DictReader(f)]
    return _csv_rows


def price_stats(code: str, region: str = "los-angeles", include_er: bool = False) -> dict | None:
    """Return a region-local cohort; ER requests never mix outpatient rows."""
    if use_db():
        sql = """
          SELECT approx_percentile(0.1, rollup(pct)) AS p10,
                 approx_percentile(0.5, rollup(pct)) AS p50,
                 approx_percentile(0.9, rollup(pct)) AS p90, sum(n) AS n
          FROM price_stats_monthly
          WHERE code = %s AND region = %s
            AND ((%s AND kind = 'er') OR (NOT %s AND kind <> 'er'))"""
        with _conn() as c:
            row = c.execute(sql, (code, region, include_er, include_er)).fetchone()
        if row and row[0] is not None:
            return {
                "p10": float(row[0]), "p50": float(row[1]), "p90": float(row[2]),
                "n": int(row[3]), "source": "tiger-data",
            }
        return None
    vals = sorted(
        r["price"] for r in _rows()
        if r["code"] == code and r["region"] == region
        and ((include_er and r["kind"] == "er") or (not include_er and r["kind"] != "er"))
    )
    if len(vals) < 10:
        return None
    deciles = statistics.quantiles(vals, n=10)
    return {
        "p10": deciles[0], "p50": statistics.median(vals), "p90": deciles[8],
        "n": len(vals), "source": "synthetic-csv",
    }


# ---------------------------------------------------------------- places
_LOCATION_PATTERNS = (
    ("chicago", "Chicago, IL", (r"\bchicago\b", r"\b606\d{2}\b")),
    ("los-angeles", "Los Angeles, CA", (r"\blos angeles\b", r"\bucla\b", r"\bwestwood\b", r"\b900\d{2}\b")),
)


def resolve_location(q: str, near: str) -> tuple[str, str]:
    """Resolve supported demo regions without silently falling back to Los Angeles."""
    requested = near.strip()
    normalized_near = requested.lower()

    # A selected/current location is authoritative, even when the query still
    # contains an older city from conversation history. UCLA is the API's
    # default rather than an explicit selection, so location words in the query
    # may override only that default.
    if requested and normalized_near not in {"ucla", "ucla, los angeles, ca"}:
        for region, label, patterns in _LOCATION_PATTERNS:
            if any(re.search(pattern, normalized_near) for pattern in patterns):
                return region, label
        return "unsupported", requested

    normalized_query = q.lower().strip()
    for region, label, patterns in _LOCATION_PATTERNS:
        if any(re.search(pattern, normalized_query) for pattern in patterns):
            return region, label

    for region, label, patterns in _LOCATION_PATTERNS:
        if any(re.search(pattern, normalized_near) for pattern in patterns):
            return region, label
    return "los-angeles", "Los Angeles, CA"


def places(region: str | None = None) -> list[dict]:
    items = json.loads((SYN / "places.json").read_text())
    if region is None:
        return items
    return [place for place in items if place.get("region", "los-angeles") == region]


# ---------------------------------------------------------------- estimates (Good Faith Estimate)
def save_estimate(case_id: str, est: dict) -> None:
    saved = {**est, "updated_at": time.time()}
    _mem["estimates"][case_id] = saved
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            c.execute(
                """INSERT INTO estimates (case_id, provider_npi, code, amount, place, payload)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (case_id, est["npi"], est["code"], est["amount"], est["place"], json.dumps(est)),
            )


def get_estimate(case_id: str) -> dict | None:
    if case_id in _mem["estimates"]:
        return _mem["estimates"][case_id]
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            row = c.execute(
                """SELECT provider_npi, code, amount, place, payload, created_at
                   FROM estimates WHERE case_id=%s ORDER BY created_at DESC LIMIT 1""",
                (case_id,),
            ).fetchone()
        if row:
            payload = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
            result = {
                "npi": row[0], "code": row[1], "amount": float(row[2]), "place": row[3],
                **payload, "updated_at": _timestamp(row[5]),
            }
            _mem["estimates"][case_id] = result
            return result
    return None


# ---------------------------------------------------------------- live visit log (hypertable)
def add_visit_event(case_id: str, item: str, code: str, est_price: float | None,
                    source_id: str = "estimated") -> None:
    _mem["visit_events"].setdefault(case_id, []).append(
        {"time": time.time(), "item": item, "code": code, "est_price": est_price,
         "source_id": source_id}
    )
    if use_db():
        with _conn() as c:
            c.execute(
                """INSERT INTO visit_events (case_id, item, code, est_price, source_id)
                   VALUES (%s,%s,%s,%s,%s)""",
                (case_id, item, code, est_price, source_id),
            )


def get_visit_events(case_id: str) -> list[dict]:
    if case_id in _mem["visit_events"]:
        return list(_mem["visit_events"][case_id])
    if use_db():
        with _conn() as c:
            rows = c.execute(
                """SELECT time, item, code, est_price, source_id FROM visit_events
                   WHERE case_id=%s ORDER BY time, code""",
                (case_id,),
            ).fetchall()
        events = [
            {"time": _timestamp(row[0]), "item": row[1] or "", "code": row[2] or "",
             "est_price": float(row[3]) if row[3] is not None else None,
             "source_id": row[4] or ("estimated" if row[3] is not None else "unpriced")}
            for row in rows
        ]
        if events:
            _mem["visit_events"][case_id] = events
        return events
    return []


def visit_running_total(case_id: str) -> tuple[float, int]:
    if use_db():
        with _conn() as c:
            row = c.execute("SELECT coalesce(sum(est_total),0), coalesce(sum(items),0) FROM visit_running_total WHERE case_id=%s",
                            (case_id,)).fetchone()
        return float(row[0]), int(row[1])
    ev = get_visit_events(case_id)
    return sum(float(e["est_price"] or 0) for e in ev), len(ev)


def visit_codes(case_id: str) -> set[str] | None:
    ev = get_visit_events(case_id) or None
    if not ev:
        return None
    # An ambiguous service is persisted once as a pipe-delimited candidate
    # set. Each candidate can explain a later bill line without pretending the
    # patient named one exact code during the visit.
    return {
        code
        for event in ev
        for code in str(event.get("code") or "").split("|")
        if code
    }


# ---------------------------------------------------------------- after-care records
def save_after_care(case_id: str, record: dict) -> None:
    saved = {**record, "updated_at": time.time()}
    _mem["after_care"][case_id] = saved
    if use_db():
        with _conn() as c:
            # Small compatibility migration for deployments created before the
            # after-care pivot. `make db` creates the same table up front.
            c.execute(
                """CREATE TABLE IF NOT EXISTS after_care_records (
                   record_id BIGSERIAL PRIMARY KEY, case_id TEXT NOT NULL, provider_npi TEXT,
                   total NUMERIC NOT NULL, already_paid BOOLEAN NOT NULL DEFAULT false,
                   payment_status TEXT NOT NULL DEFAULT 'unknown', provider_match BOOLEAN NOT NULL,
                   estimate_amount NUMERIC, estimate_difference NUMERIC, visit_items_matched INT NOT NULL DEFAULT 0,
                   payload JSONB NOT NULL, created_at TIMESTAMPTZ DEFAULT now())"""
            )
            c.execute("ALTER TABLE after_care_records ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'unknown'")
            c.execute(
                """INSERT INTO after_care_records
                   (case_id, provider_npi, total, already_paid, payment_status, provider_match, estimate_amount,
                    estimate_difference, visit_items_matched, payload)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (case_id, record["hospital_npi"], record["total"], record["payment_status"] == "paid",
                 record["payment_status"],
                 record["provider_match"], record.get("estimate_amount"), record.get("estimate_difference"),
                 record["visit_items_matched"], json.dumps(record)),
            )


def get_after_care(case_id: str) -> dict | None:
    if case_id in _mem["after_care"]:
        return _mem["after_care"][case_id]
    if use_db():
        with _conn() as c:
            row = c.execute(
                """SELECT payload, created_at FROM after_care_records
                   WHERE case_id=%s ORDER BY created_at DESC, record_id DESC LIMIT 1""",
                (case_id,),
            ).fetchone()
        if row:
            payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            result = {**payload, "updated_at": _timestamp(row[1])}
            _mem["after_care"][case_id] = result
            return result
    return None


def save_benefit_check(case_id: str, result: dict) -> None:
    _mem["benefit_checks"][case_id] = result


def get_benefit_check(case_id: str) -> dict | None:
    return _mem["benefit_checks"].get(case_id)


def save_settlement(settlement_id: str, record: dict) -> None:
    saved = {**record, "updated_at": time.time()}
    _mem["settlements"][settlement_id] = saved
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            c.execute(
                """INSERT INTO settlements
                   (settlement_id, case_id, direction, rail, amount, currency, status, external_ref, payload)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (settlement_id) DO UPDATE SET status=EXCLUDED.status,
                     payload=EXCLUDED.payload, updated_at=now()""",
                (settlement_id, record["case_id"], record["direction"], record.get("rail", "visa_qr"),
                 record.get("amount"), record.get("currency", "USD"), record["status"],
                 record.get("external_ref", ""), json.dumps(record)),
            )


def get_settlement(settlement_id: str) -> dict | None:
    if settlement_id in _mem["settlements"]:
        return _mem["settlements"][settlement_id]
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            row = c.execute(
                "SELECT payload, updated_at FROM settlements WHERE settlement_id=%s", (settlement_id,)
            ).fetchone()
        if row:
            payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            result = {**payload, "updated_at": _timestamp(row[1])}
            _mem["settlements"][settlement_id] = result
            return result
    return None


def latest_wallet_handoff(case_id: str) -> dict | None:
    matches = [
        record for record in _mem["settlements"].values()
        if record.get("case_id") == case_id and record.get("status") == "handoff_ready"
    ]
    if matches:
        return max(matches, key=lambda record: float(record.get("updated_at", 0)))
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            row = c.execute(
                """SELECT payload, updated_at FROM settlements
                   WHERE case_id=%s AND status='handoff_ready'
                   ORDER BY updated_at DESC LIMIT 1""",
                (case_id,),
            ).fetchone()
        if row:
            payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            result = {**payload, "updated_at": _timestamp(row[1])}
            if result.get("settlement_id"):
                _mem["settlements"][result["settlement_id"]] = result
            return result
    return None


# ---------------------------------------------------------------- scoped public bearer links
def save_public_link(token_hash: str, scope: str, case_id: str, subject_id: str,
                     expires_at: float) -> None:
    record = {
        "token_hash": token_hash, "scope": scope, "case_id": case_id,
        "subject_id": subject_id, "expires_at": expires_at,
    }
    _mem["public_links"][token_hash] = record
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            c.execute(
                """INSERT INTO public_access_tokens
                   (token_hash, scope, case_id, subject_id, expires_at)
                   VALUES (%s,%s,%s,%s,to_timestamp(%s))
                   ON CONFLICT (scope, subject_id) DO UPDATE SET
                     token_hash=EXCLUDED.token_hash, case_id=EXCLUDED.case_id,
                     expires_at=EXCLUDED.expires_at, updated_at=now()""",
                (token_hash, scope, case_id, subject_id, expires_at),
            )


def get_public_link(token_hash: str, scope: str) -> dict | None:
    record = _mem["public_links"].get(token_hash)
    if record and record.get("scope") == scope:
        return record
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            row = c.execute(
                """SELECT case_id, subject_id, expires_at FROM public_access_tokens
                   WHERE token_hash=%s AND scope=%s""",
                (token_hash, scope),
            ).fetchone()
        if row:
            record = {
                "token_hash": token_hash, "scope": scope, "case_id": row[0],
                "subject_id": row[1], "expires_at": _timestamp(row[2]),
            }
            _mem["public_links"][token_hash] = record
            return record
    return None


def get_public_link_by_subject(scope: str, subject_id: str) -> dict | None:
    for record in _mem["public_links"].values():
        if record.get("scope") == scope and record.get("subject_id") == subject_id:
            return record
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            row = c.execute(
                """SELECT token_hash, case_id, expires_at FROM public_access_tokens
                   WHERE scope=%s AND subject_id=%s""",
                (scope, subject_id),
            ).fetchone()
        if row:
            record = {
                "token_hash": row[0], "scope": scope, "case_id": row[1],
                "subject_id": subject_id, "expires_at": _timestamp(row[2]),
            }
            _mem["public_links"][row[0]] = record
            return record
    return None


# ---------------------------------------------------------------- channel link codes (QR join)
def save_link(code: str, case_id: str, expires_at: float, channel: str = "imessage") -> bool:
    if code in _mem["links"]:
        return False
    record = {
        "case_id": case_id, "expires_at": expires_at, "status": "waiting",
        "handle_hash": None, "space_id": None, "channel": channel,
    }
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            with c.transaction():
                row = c.execute(
                    """INSERT INTO link_codes (code, case_id, expires_at, channel)
                       VALUES (%s,%s,to_timestamp(%s),%s)
                       ON CONFLICT (code) DO NOTHING RETURNING code""",
                    (code, case_id, expires_at, channel),
                ).fetchone()
                if not row:
                    return False
                c.execute(
                    """UPDATE link_codes SET status='expired'
                       WHERE case_id=%s AND channel=%s AND status='waiting' AND code<>%s""",
                    (case_id, channel, code),
                )
    for existing_code, existing in _mem["links"].items():
        if (
            not existing_code.startswith("handle:")
            and existing.get("case_id") == case_id
            and existing.get("channel", "imessage") == channel
            and existing.get("status") == "waiting"
        ):
            existing["status"] = "expired"
    _mem["links"][code] = record
    return True


def get_link(code: str) -> dict | None:
    link = _mem["links"].get(code)
    if link is None and use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            row = c.execute(
                """SELECT case_id, expires_at, status, handle_hash, space_id, channel
                   FROM link_codes WHERE code=%s""",
                (code,),
            ).fetchone()
        if row:
            link = {
                "case_id": row[0], "expires_at": _timestamp(row[1]), "status": row[2],
                "handle_hash": row[3], "space_id": row[4], "channel": row[5] or "imessage",
            }
            _mem["links"][code] = link
    if link and link["status"] == "waiting" and time.time() > link["expires_at"]:
        link["status"] = "expired"
        if use_db():
            with _conn() as c:
                c.execute(
                    "UPDATE link_codes SET status='expired' WHERE code=%s AND status='waiting'", (code,)
                )
    return link


def claim_link(code: str, handle_hash: str, space_id: str, channel: str = "") -> dict | None:
    if use_db():
        with _conn() as c:
            _ensure_runtime_schema(c)
            row = c.execute(
                """UPDATE link_codes SET status='linked', handle_hash=%s, space_id=%s, claimed_at=now()
                   WHERE code=%s AND status='waiting' AND expires_at > now()
                     AND (%s='' OR channel=%s)
                   RETURNING case_id, expires_at, status, handle_hash, space_id, channel""",
                (handle_hash, space_id, code, channel, channel),
            ).fetchone()
            if not row:
                row = c.execute(
                    """SELECT case_id, expires_at, status, handle_hash, space_id, channel
                       FROM link_codes WHERE code=%s""",
                    (code,),
                ).fetchone()
                if not row:
                    return None
                if row[2] == "waiting" and _timestamp(row[1]) <= time.time():
                    c.execute(
                        "UPDATE link_codes SET status='expired' WHERE code=%s AND status='waiting'", (code,)
                    )
                    row = (row[0], row[1], "expired", row[3], row[4], row[5])
            link = {
                "case_id": row[0], "expires_at": _timestamp(row[1]), "status": row[2],
                "handle_hash": row[3], "space_id": row[4], "channel": row[5] or "imessage",
            }
            if channel and link["channel"] != channel:
                return {**link, "status": "channel_mismatch", "case_id": ""}
            if link["status"] == "linked" and (
                link["handle_hash"] != handle_hash or link["space_id"] != space_id
            ):
                return {**link, "status": "used", "case_id": ""}
            _mem["links"][code] = link
            if link["status"] == "linked":
                _mem["links"][f"handle:{handle_hash}"] = {"case_id": link["case_id"]}
            return link

    link = get_link(code)
    if not link:
        return None
    if link["status"] == "expired":
        return link
    if channel and link.get("channel", "imessage") != channel:
        return {**link, "status": "channel_mismatch", "case_id": ""}
    if link["status"] == "linked":
        if link.get("handle_hash") == handle_hash and link.get("space_id") == space_id:
            return link
        return {**link, "status": "used", "case_id": ""}
    if link["status"] != "waiting":
        return link
    link.update(status="linked", handle_hash=handle_hash, space_id=space_id)
    _mem["links"][f"handle:{handle_hash}"] = {"case_id": link["case_id"]}
    return link


def case_for_handle(handle_hash: str) -> str | None:
    rec = _mem["links"].get(f"handle:{handle_hash}")
    if rec:
        return rec["case_id"]
    if use_db():
        with _conn() as c:
            row = c.execute(
                """SELECT case_id FROM link_codes
                   WHERE handle_hash=%s AND status='linked' ORDER BY claimed_at DESC NULLS LAST LIMIT 1""",
                (handle_hash,),
            ).fetchone()
        if row:
            _mem["links"][f"handle:{handle_hash}"] = {"case_id": row[0]}
            return row[0]
    return None


def stop(handle_hash: str) -> None:
    _mem["stopped"].add(handle_hash)
    case_id = case_for_handle(handle_hash)
    if case_id:
        _mem["stopped"].add(f"case:{case_id}")
    for link in _mem["links"].values():
        if link.get("handle_hash") == handle_hash:
            link["status"] = "stopped"
    if use_db():
        with _conn() as c:
            c.execute(
                "UPDATE link_codes SET status='stopped' WHERE handle_hash=%s AND status='linked'",
                (handle_hash,),
            )


def reminders_allowed(case_id: str) -> bool:
    if f"case:{case_id}" in _mem["stopped"]:
        return False
    if use_db():
        with _conn() as c:
            row = c.execute(
                "SELECT 1 FROM link_codes WHERE case_id=%s AND status='stopped' LIMIT 1", (case_id,)
            ).fetchone()
        if row:
            _mem["stopped"].add(f"case:{case_id}")
            return False
    hour = time.localtime().tm_hour
    if os.getenv("BILLO_MODE", "demo") != "demo" and (hour >= 21 or hour < 8):  # quiet hours 9 pm - 8 am
        return False
    last = _mem["reminders"].get(case_id, 0)
    if os.getenv("BILLO_MODE", "demo") != "demo" and time.time() - last < 24 * 3600:  # one a day
        return False
    _mem["reminders"][case_id] = time.time()
    return True
