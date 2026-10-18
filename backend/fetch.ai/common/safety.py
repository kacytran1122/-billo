"""Deterministic helpers for emergency phrase matching."""

from __future__ import annotations

import re
from typing import Iterable


_NEGATION_PREFIXES = (
    "no",
    "without",
    "deny",
    "denies",
    "denied",
    "do not have",
    "does not have",
    "did not have",
    "don't have",
    "doesn't have",
    "didn't have",
    "not having",
)


def phrase_is_affirmed(text: str, phrase: str) -> bool:
    """Return true when at least one mention is not explicitly negated.

    This intentionally recognizes only direct negation immediately attached to
    the configured phrase. Ambiguous wording remains positive so the safety
    screen fails toward emergency guidance.
    """
    normalized = text.lower().replace("’", "'")
    # Contrast words end the scope of a preceding negation: "no chest pain,
    # but trouble breathing" must still trigger the breathing rule.
    normalized = re.sub(r"\b(?:but|however|yet)\b", ".", normalized)
    phrase_pattern = re.escape(phrase.lower()).replace(r"\ ", r"\s+")
    negation_pattern = "|".join(re.escape(prefix).replace(r"\ ", r"\s+") for prefix in _NEGATION_PREFIXES)
    negated = re.compile(
        rf"\b(?:{negation_pattern})\s+(?:any\s+)?[^.!?;,:]{{0,80}}?\b{phrase_pattern}\b"
    )
    remaining = negated.sub(" ", normalized)
    return re.search(rf"\b{phrase_pattern}\b", remaining) is not None


def first_matching_rule(text: str, rules: Iterable[dict]) -> dict | None:
    """Return the first rule with an affirmed trigger phrase."""
    for rule in rules:
        if any(phrase_is_affirmed(text, phrase) for phrase in rule["any"]):
            return rule
    return None
