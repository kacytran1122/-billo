import ast
import asyncio
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "fetch.ai"))
from common.conversation import normalize_request, payment_status, quick_reply


@pytest.mark.parametrize("text", ["hi", "Hello!", "hello there", "Hello! How are you?", "hey Billo", "good morning", "@Billo hi", "@getbillo hello", "help", "what can you do?", "start", "menu", "what is Billo?", "👋", "xin chào"])
def test_greetings_and_help_have_immediate_informative_responses(text):
    result = quick_reply(text)
    assert "Billo" in result and "https://www.getbillo.us" in result
    assert "simulated" in result


@pytest.mark.parametrize("text", ["hi, I have chest pain", "hey I can't breathe", "thanks but I need an ER", "find care near UCLA", "approve clinic payment"])
def test_mixed_symptoms_and_actions_are_not_swallowed_as_small_talk(text):
    assert quick_reply(text) is None


def test_attachments_and_asked_followups_are_not_swallowed():
    assert quick_reply("hello", has_files=True) is None
    assert quick_reply("yes", stage="booked", asked=True) is None
    assert quick_reply("no", stage="booked", asked=True) is None
    assert "What would you like" in quick_reply("yes")
    assert "Attach" in quick_reply("check my receipt")
    assert "resend" in quick_reply("this is paid")
    assert "healthcare costs" in quick_reply("tell me a joke")


@pytest.mark.parametrize("text,expected", [
    ("unpaid receipt", "unpaid"), ("not paid receipt", "unpaid"),
    ("I haven't paid this bill", "unpaid"), ("paid receipt", "paid"),
    ("I paid this bill", "paid"), ("payment confirmation", "paid"),
    ("here is a receipt", "unknown"), ("here is a prepaid estimate", "unknown"),
])
def test_payment_status_uses_boundaries_and_unpaid_wins(text, expected):
    assert payment_status(text) == expected


def coordinator_functions():
    """Exercise the actual route without starting a networked uAgent."""
    tree = ast.parse((ROOT / "backend/fetch.ai/coordinator.py").read_text())
    names = {"route_text", "step_approve_clinic_payment", "step_reimburse"}
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    nodes += [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name in names]
    env = dict(re=re, normalize_request=normalize_request, quick_reply=quick_reply,
               document_payment_status=payment_status, BILL_WORDS=("bill", "receipt"),
               QR_WORDS=("clinic qr", "scan qr"), DONE_WORDS=("they did", "x-ray"), save=lambda *args: None)
    for name in ["reply", "step_book", "step_symptoms", "step_after_care", "step_benefits", "step_visit_log", "step_scan_clinic_qr"]:
        env[name] = AsyncMock()
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "coordinator.py", "exec"), env)
    return env


def test_real_route_greets_without_calling_specialists_or_mutating_stage():
    env = coordinator_functions()
    case = {"stage": "booked", "places": []}
    asyncio.run(env["route_text"](None, case, "@Billo hi", []))
    env["reply"].assert_awaited_once()
    env["step_symptoms"].assert_not_awaited()
    assert case["stage"] == "booked"


def test_real_route_mixed_greeting_still_checks_symptoms():
    env = coordinator_functions()
    asyncio.run(env["route_text"](None, {"stage": "new", "places": []}, "hi I have chest pain", []))
    env["step_symptoms"].assert_awaited_once()


def test_real_route_handles_full_booking_numbers_and_missing_options():
    env = coordinator_functions()
    asyncio.run(env["route_text"](None, {"stage": "choosing", "places": [1]}, "book 10", []))
    assert env["step_book"].await_args.args[-1] == 10
    env = coordinator_functions()
    asyncio.run(env["route_text"](None, {"stage": "new", "places": []}, "book 1", []))
    env["step_book"].assert_not_awaited()
    env["step_symptoms"].assert_not_awaited()
    assert "Find care first" in env["reply"].await_args.args[-1]


def test_real_route_upload_uses_correct_payment_state():
    env = coordinator_functions()
    asyncio.run(env["route_text"](None, {"stage": "new", "places": []}, "unpaid receipt", ["file:test"]))
    assert env["step_after_care"].await_args.args[-1] == "unpaid"


def test_paused_settlement_blocks_both_actions():
    env = coordinator_functions()
    ctx = type("Context", (), {"send": AsyncMock()})()
    asyncio.run(env["step_approve_clinic_payment"](ctx, {"settlement_paused": True}))
    asyncio.run(env["step_reimburse"](ctx, {"settlement_paused": True}, "approve reimbursement $120 demo"))
    assert env["reply"].await_count == 2
    ctx.send.assert_not_awaited()
