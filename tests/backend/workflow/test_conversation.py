import ast
import asyncio
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "fetch.ai"))
from common.conversation import normalize_request, payment_status, quick_reply


@pytest.mark.parametrize("text", ["hi", "Hello!", "hello there", "Hello! How are you?", "hey Billo", "good morning", "@Billo hi", "@getbillo hello", "help", "what can you do?", "start", "menu", "what is Billo?", "👋", "xin chào"])
def test_greetings_and_help_have_immediate_informative_responses(text):
    result = quick_reply(text)
    assert "Billo" in result and "https://www.getbillo.us" in result
    assert "simulations" in result
    assert "no tag is needed" in result


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
    assert "care-cost questions" in quick_reply("tell me a joke")


@pytest.mark.parametrize("text,expected", [
    ("unpaid receipt", "unpaid"), ("not paid receipt", "unpaid"),
    ("I haven't paid this bill", "unpaid"), ("paid receipt", "paid"),
    ("I paid this bill", "paid"), ("payment confirmation", "paid"),
    ("here is a receipt", "unknown"), ("here is a prepaid estimate", "unknown"),
])
def test_payment_status_uses_boundaries_and_unpaid_wins(text, expected):
    assert payment_status(text) == expected


def coordinator_functions(actual=()):
    """Exercise the actual route without starting a networked uAgent."""
    tree = ast.parse((ROOT / "backend/fetch.ai/coordinator.py").read_text())
    names = {"route_text", "step_approve_clinic_payment", "step_reimburse", *actual}
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    nodes += [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in names.union({"location_hint"})
    ]
    env = dict(re=re, normalize_request=normalize_request, quick_reply=quick_reply,
               document_payment_status=payment_status, BILL_WORDS=("bill", "receipt"),
               QR_WORDS=("clinic qr", "scan qr"), DONE_WORDS=("they did", "x-ray"), save=lambda *args: None,
               say=AsyncMock(), ADDR={"gateway": "test-gateway", "payment_guard": "test-settlement",
                                      "red_flag": "test-red-flag", "care_finder": "test-care-finder"},
               OutboundText=lambda **kwargs: SimpleNamespace(**kwargs), carry=lambda: {},
               ScreenRequest=lambda **kwargs: SimpleNamespace(**kwargs), ScreenResult=SimpleNamespace,
               FindCareRequest=lambda **kwargs: SimpleNamespace(**kwargs), CareOptions=SimpleNamespace,
               dump=lambda value: vars(value), photon_care_matches=lambda *args: "care matches")
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
    assert "no current care options" in env["reply"].await_args.args[-1]


def test_real_route_upload_uses_correct_payment_state():
    env = coordinator_functions()
    asyncio.run(env["route_text"](None, {"stage": "new", "places": []}, "unpaid receipt", ["file:test"]))
    assert env["step_after_care"].await_args.args[-1] == "unpaid"


def test_location_update_reuses_the_medical_query_and_passes_chicago_to_care_finder():
    env = coordinator_functions(actual=("step_symptoms",))
    first = SimpleNamespace(emergency=False)
    chicago = SimpleNamespace(
        code="73560", location="Chicago, IL", places=[], data_mode="demo"
    )
    ctx = SimpleNamespace(send_and_receive=AsyncMock(side_effect=[(first, None), (chicago, None)]))
    case = {
        "id": "synthetic", "stage": "choosing", "places": [{"name": "old LA result"}],
        "care_query": "I broke my leg", "channel": "asi1", "who": "test-user",
    }
    asyncio.run(env["step_symptoms"](ctx, case, "I'm now in Chicago"))
    request = ctx.send_and_receive.await_args_list[1].args[1]
    assert request.near == "Chicago, IL"
    assert "I broke my leg" in request.text
    assert case["places"] == []
    assert case["location"] == "Chicago, IL"
    assert "cleared the previous location’s results" in env["reply"].await_args.args[2]


@pytest.mark.parametrize("text", ["pain in my leg", "swelling in my ankle", "find care near me"])
def test_location_parser_does_not_mistake_body_parts_or_near_me_for_a_place(text):
    env = coordinator_functions()
    assert env["location_hint"](text) is None


def test_paused_settlement_blocks_both_actions():
    env = coordinator_functions()
    ctx = type("Context", (), {"send": AsyncMock()})()
    asyncio.run(env["step_approve_clinic_payment"](ctx, {"settlement_paused": True}))
    asyncio.run(env["step_reimburse"](ctx, {"settlement_paused": True}, "approve reimbursement $120 demo"))
    assert env["reply"].await_count == 2
    ctx.send.assert_not_awaited()


def delivered_reply(env, ctx, channel):
    if channel == "asi1":
        ctx.send.assert_not_awaited()
        return env["say"].await_args.args[-1]
    env["say"].assert_not_awaited()
    assert ctx.send.await_args.args[0] == "test-gateway"
    message = ctx.send.await_args.args[1]
    assert message.space_id == "whatsapp_business:test-user"
    return message.text


@pytest.mark.parametrize("channel", ["asi1", "imessage"])  # WhatsApp uses the legacy gateway transport.
@pytest.mark.parametrize("text,expected", [
    ("hello", "I’m Billo"), ("@Billo hi", "I’m Billo"),
    ("good evening", "I’m Billo"), ("what can you help me with?", "compare care options"),
    ("help", "https://www.getbillo.us"), ("thank you", "You’re welcome"),
    ("bye", "STOP"), ("yes", "What would you like"),
    ("bill", "Attach a clear"), ("receipt", "Attach a clear"),
    ("can you check my bill?", "Attach a clear"),
    ("pay bill", "This is a simulation"), ("reimbursement", "administrator approval"),
    ("status", "describe the care"), ("book 1", "no current care options"),
    ("this is paid", "resend the document"), ("tell me a joke", "care-cost questions"),
])
def test_actual_coordinator_replies_on_the_correct_channel_without_searching(channel, text, expected):
    env = coordinator_functions(actual=("reply",))
    ctx = SimpleNamespace(send=AsyncMock())
    case = {"id": "synthetic", "stage": "new", "places": [], "channel": channel,
            "who": "asi-test-user" if channel == "asi1" else "whatsapp_business:test-user"}
    asyncio.run(env["route_text"](ctx, case, text, []))
    assert expected in delivered_reply(env, ctx, channel)
    env["step_symptoms"].assert_not_awaited()
    assert case["stage"] == "new"


@pytest.mark.parametrize("channel", ["asi1", "imessage"])
@pytest.mark.parametrize("text,expected", [
    ("check my HSA", "receipt or final bill first"),
    ("scan clinic QR", "unpaid final bill"),
    ("approve clinic payment", "verify the clinic Visa QR"),
    ("approve reimbursement $120 demo", "organize a paid receipt"),
])
def test_actual_coordinator_blocks_out_of_order_actions_on_both_channels(channel, text, expected):
    env = coordinator_functions(actual=("reply", "step_benefits", "step_scan_clinic_qr"))
    ctx = SimpleNamespace(send=AsyncMock())
    case = {"id": "synthetic", "stage": "new", "places": [], "channel": channel,
            "who": "asi-test-user" if channel == "asi1" else "whatsapp_business:test-user"}
    asyncio.run(env["route_text"](ctx, case, text, []))
    assert expected in delivered_reply(env, ctx, channel)


@pytest.mark.parametrize("channel", ["asi1", "imessage"])
@pytest.mark.parametrize("text", ["hi, I have chest pain", "hello I can't breathe"])
def test_both_channels_preserve_safety_screening_for_mixed_greetings(channel, text):
    env = coordinator_functions(actual=("reply",))
    ctx = SimpleNamespace(send=AsyncMock())
    case = {"id": "synthetic", "stage": "new", "places": [], "channel": channel, "who": "test-user"}
    asyncio.run(env["route_text"](ctx, case, text, []))
    env["step_symptoms"].assert_awaited_once()
    env["say"].assert_not_awaited()
    ctx.send.assert_not_awaited()


@pytest.mark.parametrize("stage,expected", [("booked", "not confirmed an appointment"), ("organizing", "organizing your document"), ("settled", "no real funds moved"), ("emergency", "911")])
def test_status_responses_are_stage_specific_without_inventing_success(stage, expected):
    assert expected in quick_reply("status", stage=stage)


@pytest.mark.parametrize("channel", ["asi1", "imessage"])
@pytest.mark.parametrize("text,expected", [("yes", "send the final bill"), ("no", "preferred city or ZIP code")])
def test_followup_answers_keep_their_context_instead_of_becoming_small_talk(channel, text, expected):
    env = coordinator_functions(actual=("reply",))
    ctx = SimpleNamespace(send=AsyncMock())
    case = {"id": "synthetic", "stage": "booked", "places": [], "asked": True, "channel": channel,
            "who": "asi-test-user" if channel == "asi1" else "whatsapp_business:test-user"}
    asyncio.run(env["route_text"](ctx, case, text, []))
    assert expected in delivered_reply(env, ctx, channel)
    env["step_symptoms"].assert_not_awaited()


@pytest.mark.parametrize("text,status", [("hello", "unknown"), ("help", "unknown"), ("paid receipt", "paid"), ("unpaid receipt", "unpaid")])
def test_upload_captions_take_precedence_over_quick_reply(text, status):
    env = coordinator_functions()
    asyncio.run(env["route_text"](None, {"stage": "new", "places": []}, text, ["file:synthetic"]))
    assert env["step_after_care"].await_args.args[-2:] == ("file:synthetic", status)
    env["reply"].assert_not_awaited()


@pytest.mark.parametrize("channel", ["asi1", "imessage"])
def test_stop_cancels_reminders_on_both_coordinator_paths(channel):
    env = coordinator_functions(actual=("reply",))
    ctx = SimpleNamespace(send=AsyncMock())
    case = {"id": "synthetic", "stage": "booked", "places": [], "followup_due": 100, "channel": channel,
            "who": "asi-test-user" if channel == "asi1" else "whatsapp_business:test-user"}
    asyncio.run(env["route_text"](ctx, case, "STOP", []))
    assert case["stopped"] is True and case["followup_due"] == 0
    assert "Stopped" in delivered_reply(env, ctx, channel)


def test_display_name_changes_without_changing_the_seed_configuration():
    source = (ROOT / "backend/fetch.ai/coordinator.py").read_text()
    assert 'name="Billo"' in source
    assert 'seed=require_seed("coordinator")' in source
