"""Data access. Uses Tiger Data (Postgres + TimescaleDB) when DATABASE_URL is set,
otherwise an in-memory store + the synthetic CSV, so the demo always runs.
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYN = ROOT / "data" / "synthetic"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

_mem: dict[str, dict] = {
    "estimates": {}, "visit_events": {}, "after_care": {}, "benefit_checks": {},
    "links": {}, "payments": {}, "stopped": set(), "reminders": {},
}


def _conn():
    import psycopg  # imported lazily so the demo works without it
    return psycopg.connect(DATABASE_URL, autocommit=True)


def use_db() -> bool:
    return bool(DATABASE_URL) and "PASSWORD@HOST" not in DATABASE_URL


# ---------------------------------------------------------------- prices
_csv_rows: list[dict] | None = None


def _rows() -> list[dict]:
    global _csv_rows
    if _csv_rows is None:
        with open(SYN / "prices.csv") as f:
            _csv_rows = [{**r, "price": float(r["price"])} for r in csv.DictReader(f)]
    return _csv_rows


def price_stats(code: str, region: str = "los-angeles", include_er: bool = False) -> dict | None:
    if use_db():
        sql = """
          SELECT approx_percentile(0.5, rollup(pct)) AS p50, approx_percentile(0.9, rollup(pct)) AS p90,
                 sum(n) AS n
          FROM price_stats_monthly
          WHERE code = %s AND region = %s AND (%s OR kind <> 'er')"""
        with _conn() as c:
            row = c.execute(sql, (code, region, include_er)).fetchone()
        if row and row[0] is not None:
            return {"p50": float(row[0]), "p90": float(row[1]), "n": int(row[2]), "source": "tiger-data"}
        return None
    vals = sorted(r["price"] for r in _rows() if r["code"] == code and r["region"] == region and (include_er or r["kind"] != "er"))
    if len(vals) < 10:
        return None
    return {"p50": statistics.median(vals), "p90": statistics.quantiles(vals, n=10)[8], "n": len(vals), "source": "synthetic-csv"}


# ---------------------------------------------------------------- places
def places() -> list[dict]:
    return json.loads((SYN / "places.json").read_text())


# ---------------------------------------------------------------- estimates (Good Faith Estimate)
def save_estimate(case_id: str, est: dict) -> None:
    _mem["estimates"][case_id] = est
    if use_db():
        with _conn() as c:
            c.execute("INSERT INTO estimates (case_id, provider_npi, code, amount, place) VALUES (%s,%s,%s,%s,%s)",
                      (case_id, est["npi"], est["code"], est["amount"], est["place"]))


def get_estimate(case_id: str) -> dict | None:
    if case_id in _mem["estimates"]:
        return _mem["estimates"][case_id]
    if use_db():
        with _conn() as c:
            row = c.execute("SELECT provider_npi, code, amount, place FROM estimates WHERE case_id=%s ORDER BY created_at DESC LIMIT 1",
                            (case_id,)).fetchone()
        if row:
            return {"npi": row[0], "code": row[1], "amount": float(row[2]), "place": row[3]}
    return None


# ---------------------------------------------------------------- live visit log (hypertable)
def add_visit_event(case_id: str, item: str, code: str, est_price: float) -> None:
    _mem["visit_events"].setdefault(case_id, []).append({"time": time.time(), "item": item, "code": code, "est_price": est_price})
    if use_db():
        with _conn() as c:
            c.execute("INSERT INTO visit_events (case_id, item, code, est_price) VALUES (%s,%s,%s,%s)", (case_id, item, code, est_price))


def visit_running_total(case_id: str) -> tuple[float, int]:
    if use_db():
        with _conn() as c:
            row = c.execute("SELECT coalesce(sum(est_total),0), coalesce(sum(items),0) FROM visit_running_total WHERE case_id=%s",
                            (case_id,)).fetchone()
        return float(row[0]), int(row[1])
    ev = _mem["visit_events"].get(case_id, [])
    return sum(e["est_price"] for e in ev), len(ev)


def visit_codes(case_id: str) -> set[str] | None:
    ev = _mem["visit_events"].get(case_id)
    if ev is None and use_db():
        with _conn() as c:
            rows = c.execute("SELECT code FROM visit_events WHERE case_id=%s", (case_id,)).fetchall()
        ev = [{"code": r[0]} for r in rows] or None
    return {e["code"] for e in ev} if ev else None


# ---------------------------------------------------------------- after-care records
def save_after_care(case_id: str, record: dict) -> None:
    _mem["after_care"][case_id] = record
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


def save_benefit_check(case_id: str, result: dict) -> None:
    _mem["benefit_checks"][case_id] = result


# ---------------------------------------------------------------- iMessage link codes (QR join)
def save_link(code: str, case_id: str, expires_at: float) -> None:
    _mem["links"][code] = {"case_id": case_id, "expires_at": expires_at, "status": "waiting", "handle_hash": None}
    if use_db():
        with _conn() as c:
            c.execute("INSERT INTO link_codes (code, case_id, expires_at) VALUES (%s,%s,to_timestamp(%s))", (code, case_id, expires_at))


def get_link(code: str) -> dict | None:
    return _mem["links"].get(code)


def claim_link(code: str, handle_hash: str, space_id: str) -> dict | None:
    link = _mem["links"].get(code)
    if not link:
        return None
    if time.time() > link["expires_at"]:
        link["status"] = "expired"
        return link
    if link["status"] == "linked":  # idempotent: a resent code returns the same result
        return link
    link.update(status="linked", handle_hash=handle_hash, space_id=space_id)
    _mem["links"][f"handle:{handle_hash}"] = {"case_id": link["case_id"]}
    return link


def case_for_handle(handle_hash: str) -> str | None:
    rec = _mem["links"].get(f"handle:{handle_hash}")
    return rec["case_id"] if rec else None


def stop(handle_hash: str) -> None:
    _mem["stopped"].add(handle_hash)
    case_id = case_for_handle(handle_hash)
    if case_id:
        _mem["stopped"].add(f"case:{case_id}")
    for link in _mem["links"].values():
        if link.get("handle_hash") == handle_hash:
            link["status"] = "stopped"


def reminders_allowed(case_id: str) -> bool:
    if f"case:{case_id}" in _mem["stopped"]:
        return False
    hour = time.localtime().tm_hour
    if os.getenv("BILLO_MODE", "demo") != "demo" and (hour >= 21 or hour < 8):  # quiet hours 9 pm - 8 am
        return False
    last = _mem["reminders"].get(case_id, 0)
    if os.getenv("BILLO_MODE", "demo") != "demo" and time.time() - last < 24 * 3600:  # one a day
        return False
    _mem["reminders"][case_id] = time.time()
    return True


# ---------------------------------------------------------------- payments
def save_payment(payment_id: str, rec: dict) -> None:
    _mem["payments"][payment_id] = rec


def get_payment(payment_id: str) -> dict | None:
    return _mem["payments"].get(payment_id)
