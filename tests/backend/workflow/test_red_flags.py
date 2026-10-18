"""Regression tests for the deterministic emergency phrase matcher."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "fetch.ai"))

from common.safety import first_matching_rule  # noqa: E402


RULES = yaml.safe_load((ROOT / "backend" / "rules" / "red_flags.yaml").read_text())["rules"]


def match(text: str) -> str | None:
    rule = first_matching_rule(text, RULES)
    return rule["id"] if rule else None


def test_explicitly_negated_emergency_phrases_do_not_stop_care_search():
    assert match("I can walk and I do not have chest pain or trouble breathing") is None
    assert match("No chest pain and no trouble breathing") is None
    assert match("I twisted my knee without chest pain") is None
    assert match("I don't have any chest pressure") is None
    assert match("I have no chest pain or trouble breathing") is None


def test_affirmed_or_ambiguous_emergency_phrases_still_stop_the_workflow():
    assert match("I have chest pain") == "RF-CHEST"
    assert match("I can't breathe") == "RF-BREATH"
    assert match("No chest pain, but now I have trouble breathing") == "RF-BREATH"
    assert match("It is not only chest pain; I also feel crushing pressure") == "RF-CHEST"
