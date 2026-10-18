"""Turn OCR boxes into typed bill lines. Pure code, no AI, fully testable."""
from __future__ import annotations

import re
from statistics import median

from .engine import Box

MONEY = re.compile(r"\(?-?\$?\s?\d{1,3}(?:,\d{3})*\.\d{2}\)?|\(?-?\$?\s?\d+\.\d{2}\)?")
DATE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")
CPT = re.compile(r"\b(\d{4}[0-9FTU])(?:-?([0-9A-Z]{2}))?\b")  # CPT incl. Cat II/III
HCPCS = re.compile(r"\b([A-V]\d{4})(?:-?([0-9A-Z]{2}))?\b")
REV = re.compile(r"\b(0\d{3})\b")  # UB-04 revenue code (0250 pharmacy, 0120 room...)
NPI = re.compile(r"\bNPI\b[\s:#]*(\d{10})\b", re.I)
INT = re.compile(r"^\d{1,3}$")

SKIP = re.compile(
    r"\b(sub\s?total|total|balance|amount\s+due|payments?|paid|adjust\w*|discounts?|insurance|"
    r"deductible|copay|coinsurance|previous|statement|page\s+\d)\b",
    re.I,
)
TOTAL = re.compile(r"\b(total\s+charges|total|amount\s+due|balance\s+due)\b", re.I)


def money_to_float(s: str) -> float:
    neg = s.strip().startswith(("(", "-"))
    v = float(re.sub(r"[^\d.]", "", s) or 0)
    return -v if neg else v


def group_rows(boxes: list[Box]) -> list[list[Box]]:
    """Cluster boxes into visual rows by vertical center, then sort each row left to right."""
    if not boxes:
        return []
    tol = 0.55 * median(b.h for b in boxes)
    rows: list[list[Box]] = []
    for b in sorted(boxes, key=lambda b: b.cy):
        if rows and abs(b.cy - sum(x.cy for x in rows[-1]) / len(rows[-1])) <= tol:
            rows[-1].append(b)
        else:
            rows.append([b])
    return [sorted(r, key=lambda b: b.x0) for r in rows]


def _norm_date(m: re.Match) -> str:
    if m.group(4):
        return f"{m.group(4)}-{m.group(5)}-{m.group(6)}"
    mo, d, y = int(m.group(1)), int(m.group(2)), m.group(3)
    y = int(y) + 2000 if len(y) == 2 else int(y)
    return f"{y:04d}-{mo:02d}-{d:02d}"


def parse_row(row: list[Box]) -> dict | None:
    """Parse one visual row. Returns a line dict, or None if it is not a charge line."""
    text = " ".join(b.text for b in row)
    if SKIP.search(text):
        return None
    monies = [(m.group(), m.start()) for m in MONEY.finditer(text)]
    if not monies:
        return None
    charge = money_to_float(monies[-1][0])  # rightmost amount = line total
    if charge <= 0:
        return None

    # Boxes left of the first amount; a box that is only a small integer is the QTY column.
    left = [b for b in row if not MONEY.search(b.text)]
    qty_box = next((b for b in reversed(left) if INT.match(b.text)), None)
    rest = " ".join(b.text for b in left if b is not qty_box)

    service_date = ""
    if dm := DATE.search(rest):
        service_date = _norm_date(dm)
        rest = rest[: dm.start()] + " " + rest[dm.end():]

    rev_code = ""
    if rm := REV.search(rest):
        rev_code = rm.group(1)
        rest = rest[: rm.start()] + " " + rest[rm.end():]

    code, modifier = "", ""
    cm = HCPCS.search(rest) or CPT.search(rest)
    if cm:
        code, modifier = cm.group(1), cm.group(2) or ""
        rest = rest[: cm.start()] + " " + rest[cm.end():]

    # Units. Best evidence: unit price x qty = total. Next: a QTY-column box. Else 1.
    units = int(qty_box.text) if qty_box and 0 < int(qty_box.text) < 1000 else 1
    if len(monies) >= 2:
        unit_price = money_to_float(monies[-2][0])
        if unit_price > 0:
            ratio = charge / unit_price
            if abs(ratio - round(ratio)) < 0.01 and 1 <= round(ratio) < 1000:
                units = round(ratio)

    description = re.sub(r"\s+", " ", rest).strip(" -:|")[:120]
    return {
        "code": code,
        "modifier": modifier,
        "rev_code": rev_code,
        "description": description,
        "units": units,
        "charge": round(charge, 2),
        "service_date": service_date,
        "confidence": round(min(b.conf for b in row), 3),
        "bbox": [
            round(min(b.x0 for b in row)), round(min(b.y0 for b in row)),
            round(max(b.x1 for b in row)), round(max(b.y1 for b in row)),
        ],
    }


def find_total(rows: list[list[Box]]) -> float | None:
    """Printed bill total, used to sanity-check the parsed lines."""
    for row in reversed(rows):
        text = " ".join(b.text for b in row)
        if TOTAL.search(text) and not re.search(r"payment|paid|adjust|insurance", text, re.I):
            monies = MONEY.findall(text)
            if monies:
                return money_to_float(monies[-1])
    return None


def parse_bill(boxes: list[Box]) -> dict:
    """OCR boxes -> {hospital_npi, lines, unreviewed_lines, printed_total, totals_match}."""
    rows = group_rows(boxes)
    full = " ".join(b.text for b in boxes)
    m = NPI.search(full)
    npi = m.group(1) if m else ""

    lines, unreviewed = [], []
    for row in rows:
        line = parse_row(row)
        if not line:
            continue
        # Lines with no CPT/HCPCS code (room, pharmacy, supplies) are kept for the
        # user to review instead of being silently dropped.
        (lines if line["code"] else unreviewed).append(line)
    for i, line in enumerate(lines, 1):
        line["line_no"] = i

    total = find_total(rows)
    parsed_sum = round(sum(l["charge"] for l in lines + unreviewed), 2)
    totals_match = None if total is None else abs(parsed_sum - total) <= max(0.02, 0.01 * total)
    return {
        "hospital_npi": npi,
        "lines": lines,
        "unreviewed_lines": unreviewed,
        "printed_total": total,
        "parsed_total": parsed_sum,
        "totals_match": totals_match,
    }
