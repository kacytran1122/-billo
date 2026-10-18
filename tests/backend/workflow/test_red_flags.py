"""Regression tests for the deterministic emergency phrase matcher."""

from __future__ import annotations

import ast
import asyncio
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

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


def test_red_flag_handler_logs_no_case_or_screening_result():
    tree = ast.parse((ROOT / "backend/fetch.ai/red_flag.py").read_text())
    handler = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "on_screen"
    )
    handler.decorator_list = []
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    result = SimpleNamespace(case_id="", emergency=True, rule_id="RF-CHEST", message="Call 911")
    env = {
        "case_span": lambda *_args, **_kwargs: nullcontext(),
        "screen": Mock(return_value=result),
        "carry": Mock(return_value={}),
    }
    exec(
        compile(ast.fix_missing_locations(ast.Module(body=[future, handler], type_ignores=[])),
                "red_flag.py", "exec"),
        env,
    )
    ctx = SimpleNamespace(logger=Mock(), send=AsyncMock())
    request = SimpleNamespace(case_id="private-case-123", text="I have chest pain")

    asyncio.run(env["on_screen"](ctx, "sender", request))

    ctx.logger.info.assert_called_once_with("red-flag screen completed")
    encoded_log = str(ctx.logger.info.call_args)
    assert request.case_id not in encoded_log
    assert request.case_id[:6] not in encoded_log
    assert result.rule_id not in encoded_log
    assert "emergency" not in encoded_log
