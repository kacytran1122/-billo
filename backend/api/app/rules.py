"""Bill audit rules + the two-check vote. Pure functions: easy to test, no I/O.

rules check : is a fixed billing rule broken?  (DUP-001, NCCI-PTP, NOT-IN-LOG)
price check : is the money too high?           (above p90 for the code in the area)
vote        : dispute ONLY when both agree; one alone -> "ask the hospital"
"""
from __future__ import annotations

from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RULES = yaml.safe_load((BACKEND_ROOT / "rules" / "bill_audit.yaml").read_text())


def rules_check(line: dict, all_lines: list[dict], visit_codes: set[str] | None) -> list[tuple[str, str]]:
    """Return [(rule_id, reason)] for this line."""
    hits: list[tuple[str, str]] = []
    if not line.get("code"):
        return hits  # Uncoded receipt items need review, not invented code rules.
    same = [l for l in all_lines if l["code"] == line["code"] and l.get("service_date") == line.get("service_date")]
    if len(same) > 1 and line["line_no"] != min(l["line_no"] for l in same):
        hits.append((RULES["duplicates"]["rule_id"], f"code {line['code']} is billed {len(same)} times on the same day"))
    codes_today = {l["code"] for l in all_lines if l.get("service_date") == line.get("service_date")}
    for a, b in RULES["ncci"]["pairs"]:
        if line["code"] == b and a in codes_today:
            hits.append((RULES["ncci"]["rule_id"], f"codes {a} and {b} should not be billed together (NCCI)"))
    vl = RULES["visit_log"]
    if visit_codes is not None and line["code"] not in vl["always_ok"] and line["code"] not in visit_codes:
        hits.append((vl["rule_id"], f"nothing in your visit log explains code {line['code']}"))
    return hits


def price_check(line: dict, all_lines: list[dict], stats: dict | None) -> tuple[bool, str, float]:
    """Return (too_high, reason, amount_over_typical) using p50/p90 for the code."""
    if not stats:
        return False, "no price data for this code", 0.0
    same = [l for l in all_lines if l["code"] == line["code"] and l.get("service_date") == line.get("service_date")]
    billed_for_code = sum(l["charge"] for l in same)
    p50, p90 = stats["p50"], stats["p90"]
    if len(same) > 1 and line["line_no"] != min(l["line_no"] for l in same):
        too_high = billed_for_code > p90  # duplicate: together they cost more than one normal service
        return too_high, f"together ${billed_for_code:,.0f} vs. ${p90:,.0f} for one (90% of area prices)", line["charge"]
    too_high = line["charge"] > p90
    return too_high, f"${line['charge']:,.0f} vs. ${p50:,.0f} typical and ${p90:,.0f} at 90% of area prices", max(0.0, line["charge"] - p50)


def vote(line: dict, rule_hits: list[tuple[str, str]], price: tuple[bool, str, float]) -> dict | None:
    too_high, price_reason, over = price
    if not rule_hits and not too_high:
        return None
    both = bool(rule_hits) and too_high
    rule_id = rule_hits[0][0] if rule_hits else RULES["price"]["rule_id"]
    reason = rule_hits[0][1] if rule_hits else "no billing rule is broken, but the price is very high"
    return {
        "rule_id": rule_id,
        "kind": "dispute" if both else "ask_hospital",
        "rules_check": bool(rule_hits),
        "price_check": too_high,
        "line_nos": [line["line_no"]],
        "amount_at_stake": round(line["charge"] if rule_hits else over, 2),
        "explanation": f"line {line['line_no']} ({line['description']}): {reason}; {price_reason}",
        "source_ids": [rule_id, f"price:{line['code']}"],
    }


def say_for(line: dict, flag: dict | None) -> str:
    if not flag:
        return f"{line['description']} looks fine."
    if flag["kind"] == "dispute":
        return f"{line['description']}: both checks agree this is wrong. It goes in the dispute letter."
    which = "the price check" if flag["price_check"] else "the rules check"
    return f"{line['description']}: only {which} found a problem, so I will ask the hospital instead of disputing."


def gfe_check(lines: list[dict], gfe: float | None, sum_p90: float) -> dict | None:
    """Case level: No Surprises Act. Dispute if billed >= GFE + $400 AND the total is above normal prices."""
    if gfe is None:
        return None
    total = sum(l["charge"] for l in lines)
    over = total - gfe
    rules_hit = over >= RULES["gfe"]["threshold"]
    price_hit = total > sum_p90
    if not rules_hit:
        return None
    return {
        "rule_id": RULES["gfe"]["rule_id"],
        "kind": "dispute" if price_hit else "ask_hospital",
        "rules_check": True,
        "price_check": price_hit,
        "line_nos": [l["line_no"] for l in lines],
        "amount_at_stake": round(over, 2),
        "explanation": (f"the total ${total:,.0f} is ${over:,.0f} over your Good Faith Estimate of ${gfe:,.0f} "
                        f"(you can dispute within {RULES['gfe']['dispute_window_days']} days)"),
        "source_ids": ["GFE-400", "gfe:saved"],
    }


def disputed_amount(lines: list[dict], flags: list[dict], gfe: float | None) -> float:
    """If the $400 rule applies, the patient pays the estimate and disputes the rest."""
    total = sum(l["charge"] for l in lines)
    line_disputes = sum(f["amount_at_stake"] for f in flags if f["kind"] == "dispute" and f["rule_id"] != "GFE-400")
    gfe_flag = any(f["rule_id"] == "GFE-400" and f["kind"] == "dispute" for f in flags)
    if gfe_flag and gfe is not None:
        return round(max(line_disputes, total - gfe), 2)
    return round(line_disputes, 2)


def visit_codes_from_text(text: str) -> set[str]:
    low = text.lower()
    out: set[str] = set()
    for word, codes in RULES["visit_log"]["words"].items():
        if word in low:
            out.update(codes)
    return out
