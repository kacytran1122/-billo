"""Cross-check lines from the vision model (ChatGPT) against what OCR actually saw.

A vision model can misread or invent a number. OCR is literal. A line is
`verified` only if both its charge and its code appear in the OCR text.
"""
from __future__ import annotations

import re

from .engine import Box
from .parse import MONEY, money_to_float


def _index(boxes: list[Box]) -> tuple[dict[int, list[int]], set[str], str]:
    cents: dict[int, list[int]] = {}
    for b in boxes:
        for m in MONEY.findall(b.text):
            cents.setdefault(round(abs(money_to_float(m)) * 100), b.bbox())
    blob = " ".join(b.text for b in boxes).upper()
    tokens = set(re.findall(r"[A-Z0-9]+", blob))
    return cents, tokens, blob


def verify_lines(lines: list[dict], boxes: list[Box] | None) -> list[dict]:
    """Add `verified` (True/False, or None if no OCR) and `check` to each line."""
    if not boxes:
        for l in lines:
            l["verified"] = None
        return lines
    cents, tokens, _ = _index(boxes)
    for l in lines:
        c = round(abs(float(l.get("charge", 0))) * 100)
        code = str(l.get("code", "")).upper().replace(" ", "")
        charge_ok = c in cents
        code_ok = bool(code) and (code in tokens or code.split("-")[0] in tokens)
        l["check"] = {"charge_seen": charge_ok, "code_seen": code_ok}
        l["verified"] = charge_ok and code_ok
        if charge_ok:
            l.setdefault("bbox", cents[c])
    return lines
