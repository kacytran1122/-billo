"""Concurrency, recovery, and bearer-boundary regressions for Coordinator."""
import ast
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/fetch.ai"))


def coordinator_functions(names, env):
    tree = ast.parse((ROOT / "backend/fetch.ai/coordinator.py").read_text())
    future = ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0,
    )
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            # Unit-exec the function body without requiring the uAgents runtime
            # that owns its production decorator.
            node.decorator_list = [
                decorator for decorator in node.decorator_list
                if isinstance(decorator, ast.Name) and decorator.id == "asynccontextmanager"
            ]
            selected.append(node)
    nodes = [future] + selected
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
            "coordinator.py",
            "exec",
        ),
        env,
    )
    return env


def locking_functions():
    return coordinator_functions({
        "_operation_state_lock", "_next_turn_sequence", "_register_case_turn",
        "_case_turn", "_register_door_turn", "_door_turn",
    }, {
        "asyncio": asyncio,
        "time": time,
        "asynccontextmanager": asynccontextmanager,
        "_OPERATION_STATE_LOCKS": {},
        "_CASE_TURN_GENERATIONS": {},
        "_CASE_EMERGENCY_GENERATIONS": {},
        "_CASE_PRIORITY_INGRESS_GENERATIONS": {},
        "_CASE_PRIORITY_COMPLETED_GENERATIONS": {},
        "_CASE_PENDING_TURNS": {},
        "_CASE_TURN_CONDITIONS": {},
        "_ACTIVE_CASE_TURNS": {},
        "_ACTIVE_CASE_TURN_LEVELS": {},
        "_DOOR_TURN_LOCKS": {},
        "_DOOR_TURN_GENERATIONS": {},
        "_DOOR_PRIORITY_GENERATIONS": {},
        "_DOOR_EMERGENCY_GENERATIONS": {},
        "_DOOR_EMERGENCY_COMPLETED_GENERATIONS": {},
        "_DOOR_PENDING_TURNS": {},
        "_DOOR_TURN_CONDITIONS": {},
        "_ACTIVE_DOOR_TURNS": {},
        "_ACTIVE_DOOR_TURN_LEVELS": {},
        "_TURN_SEQUENCE": 0,
    })


def test_linked_emergency_invalidates_an_older_turn_still_waiting_at_another_door():
    env = locking_functions()

    async def exercise():
        active = asyncio.Event()
        older_registered = asyncio.Event()
        emergency_finished = asyncio.Event()
        case_id = "linked-case"

        async def active_whatsapp_turn():
            arrival = env["_next_turn_sequence"]()
            door_generation = env["_register_door_turn"]("whatsapp", arrival)
            async with env["_door_turn"]("whatsapp", door_generation) as door_current:
                assert door_current
                case_generation = env["_register_case_turn"](case_id, arrival)
                async with env["_case_turn"](case_id, case_generation) as case_current:
                    assert case_current
                    active.set()
                    await asyncio.Event().wait()

        async def older_waiting_whatsapp_turn():
            arrival = env["_next_turn_sequence"]()
            door_generation = env["_register_door_turn"]("whatsapp", arrival)
            older_registered.set()
            async with env["_door_turn"]("whatsapp", door_generation) as door_current:
                assert door_current
                case_generation = env["_register_case_turn"](case_id, arrival)
                async with env["_case_turn"](case_id, case_generation) as case_current:
                    return case_current

        async def asi_emergency_turn():
            arrival = env["_next_turn_sequence"]()
            door_generation = env["_register_door_turn"]("asi", arrival, emergency=True)
            async with env["_door_turn"](
                "asi", door_generation, emergency=True,
            ) as door_current:
                assert door_current
                case_generation = env["_register_case_turn"](
                    case_id, arrival, emergency=True,
                )
                async with env["_case_turn"](
                    case_id, case_generation, emergency=True,
                ) as case_current:
                    assert case_current
                    emergency_finished.set()

        active_task = asyncio.create_task(active_whatsapp_turn())
        await active.wait()
        older_task = asyncio.create_task(older_waiting_whatsapp_turn())
        await older_registered.wait()
        emergency_task = asyncio.create_task(asi_emergency_turn())

        await emergency_finished.wait()
        assert await older_task is False
        await emergency_task
        with pytest.raises(asyncio.CancelledError):
            await active_task

    asyncio.run(exercise())


def test_slow_emergency_registration_cannot_be_overtaken_by_a_faster_normal_ack():
    env = locking_functions()

    async def exercise():
        emergency_arrival = env["_next_turn_sequence"]()
        emergency_generation = env["_register_door_turn"](
            "asi", emergency_arrival, emergency=True,
        )

        # This represents a later ordinary message whose acknowledgement
        # returns while the emergency acknowledgement is still in flight.
        normal_arrival = env["_next_turn_sequence"]()
        normal_generation = env["_register_door_turn"]("asi", normal_arrival)
        normal_entered = asyncio.Event()

        async def run_normal():
            async with env["_door_turn"]("asi", normal_generation) as current:
                assert current is True
                normal_entered.set()

        normal_task = asyncio.create_task(run_normal())
        await asyncio.sleep(0)
        assert not normal_entered.is_set()

        async with env["_door_turn"](
            "asi", emergency_generation, emergency=True,
        ) as current:
            assert current is True

        await normal_task
        assert normal_entered.is_set()

        # Once safety guidance completes, a genuinely later message is usable.
        later_arrival = env["_next_turn_sequence"]()
        later_generation = env["_register_door_turn"]("asi", later_arrival)
        async with env["_door_turn"]("asi", later_generation) as current:
            assert current is True

    asyncio.run(exercise())


def test_ordinary_turns_remain_fifo_when_acknowledgements_finish_out_of_order():
    env = locking_functions()

    async def exercise():
        first_arrival = env["_next_turn_sequence"]()
        first_generation = env["_register_door_turn"]("asi", first_arrival)
        second_arrival = env["_next_turn_sequence"]()
        second_generation = env["_register_door_turn"]("asi", second_arrival)
        third_arrival = env["_next_turn_sequence"]()
        third_generation = env["_register_door_turn"]("asi", third_arrival)
        order = []
        release_first = asyncio.Event()

        async def run(generation, label, gate=None):
            async with env["_door_turn"]("asi", generation) as current:
                assert current is True
                order.append(label)
                if gate is not None:
                    await gate.wait()

        first = asyncio.create_task(run(first_generation, "first", release_first))
        await asyncio.sleep(0)
        # Simulate the third acknowledgement returning before the second.
        third = asyncio.create_task(run(third_generation, "third"))
        await asyncio.sleep(0)
        second = asyncio.create_task(run(second_generation, "second"))
        await asyncio.sleep(0)
        assert order == ["first"]
        release_first.set()
        await asyncio.gather(first, second, third)
        assert order == ["first", "second", "third"]

    asyncio.run(exercise())


def test_stop_cannot_cancel_an_active_emergency_response():
    env = locking_functions()

    async def exercise():
        emergency_arrival = env["_next_turn_sequence"]()
        emergency_generation = env["_register_door_turn"](
            "asi", emergency_arrival, priority=True, emergency=True,
        )
        emergency_started = asyncio.Event()
        release_emergency = asyncio.Event()

        async def run_emergency():
            async with env["_door_turn"](
                "asi", emergency_generation, priority=True, emergency=True,
            ) as current:
                assert current is True
                emergency_started.set()
                await release_emergency.wait()

        emergency_task = asyncio.create_task(run_emergency())
        await emergency_started.wait()
        stop_arrival = env["_next_turn_sequence"]()
        stop_generation = env["_register_door_turn"](
            "asi", stop_arrival, priority=True, emergency=False,
        )

        async def run_stop():
            async with env["_door_turn"](
                "asi", stop_generation, priority=True, emergency=False,
            ) as current:
                return current

        stop_task = asyncio.create_task(run_stop())
        await asyncio.sleep(0)
        assert not emergency_task.done()
        assert not stop_task.done()
        release_emergency.set()
        await emergency_task
        assert await stop_task is True

    asyncio.run(exercise())


def reconciliation_functions(case, responses):
    from common.models import AfterCareResult, SettlementResult

    async def core_post(path, body):
        responses.append((path, deepcopy(body)))
        if path == "/operations/status":
            return responses.status
        return {"canceled": False}

    env = {
        "asyncio": asyncio,
        "time": SimpleNamespace(time=lambda: 1_000),
        "OPERATION_TIMEOUT_SECONDS": 330,
        "load": lambda ctx, case_id: case,
        "core_post": core_post,
        "sentry_sdk": SimpleNamespace(capture_message=Mock()),
        "AfterCareResult": AfterCareResult,
        "SettlementResult": SettlementResult,
        "carry": lambda: {},
        "_apply_after_care_result": AsyncMock(),
        "_apply_settlement_result": AsyncMock(),
        "_ACTIVE_RESULT_TURNS": {},
        "_COMMITTED_RESULT_TURNS": set(),
        "save": Mock(),
        "reply": AsyncMock(),
    }
    return coordinator_functions({
        "_after_care_replay", "_settlement_replay", "_reconcile_timed_out_operations",
    }, env)


class Responses(list):
    status = None


def test_completed_reconciliation_replays_minimal_result_silently_for_new_turn():
    case = {
        "id": "case-1", "stage": "organizing", "pending_after_care_id": "request-1",
        "pending_after_care_started_at": 600,
    }
    responses = Responses()
    responses.status = {
        "status": "completed", "action": "after_care", "result": {
            "total": 42.5, "hospital_npi": "123", "payment_status": "paid",
            "provider_match": True, "reader": "ocr", "unreviewed_lines": [2],
            "needs_review": [3], "next_steps": ["No payment is needed."],
        },
    }
    env = reconciliation_functions(case, responses)

    changed = asyncio.run(env["_reconcile_timed_out_operations"](
        None, case, now=1_000, deliver=False,
    ))

    assert changed is True
    replay = env["_apply_after_care_result"].await_args.args[1]
    assert replay.lines == [] and replay.total == 42.5
    assert replay.unreviewed_lines == 1 and replay.needs_review == [3]
    assert env["_apply_after_care_result"].await_args.kwargs == {"notify": False}
    assert all("lines" not in body for _, body in responses)


def test_result_after_a_queued_superseding_user_turn_updates_silently():
    case = {
        "id": "case-1", "pending_after_care_id": "request-1",
        "pending_after_care_generation": 1,
    }

    @asynccontextmanager
    async def permit(*args, **kwargs):
        yield True

    env = coordinator_functions({"on_result"}, {
        "ADDR": {"bill_auditor": "auditor"},
        "_next_turn_sequence": lambda: 3,
        "_register_case_turn": lambda case_id, generation: generation,
        "_case_turn": permit,
        "load": lambda ctx, case_id: case,
        "_CASE_SUPERSEDING_USER_ARRIVALS": {"case-1": 2},
        "_ACTIVE_RESULT_TURNS": {},
        "_COMMITTED_RESULT_TURNS": set(),
        "asyncio": asyncio,
        "_apply_after_care_result": AsyncMock(),
    })

    result = SimpleNamespace(case_id="case-1", request_id="request-1")
    asyncio.run(env["on_result"](None, "auditor", result))

    env["_apply_after_care_result"].assert_awaited_once_with(
        None, result, notify=False,
    )


def test_result_reply_rechecks_supersession_after_case_link_await():
    started = asyncio.Event()
    release = asyncio.Event()
    watermark = {"case-1": 1}
    say = AsyncMock()

    async def core_post(path, body):
        assert path == "/case-links"
        started.set()
        await release.wait()
        return {"visit_url": "https://www.getbillo.us/visit/opaque"}

    env = coordinator_functions({"reply"}, {
        "_CASE_SUPERSEDING_USER_ARRIVALS": watermark,
        "_REPLY_TARGET": None,
        "_is_group_target": lambda *args: False,
        "screen_for": lambda *args: "visit",
        "with_screen_link": lambda text, stage, url: f"{text} {url}".strip(),
        "core_post": core_post,
        "sentry_sdk": SimpleNamespace(capture_message=Mock()),
        "say": say,
        "ADDR": {"gateway": "gateway"},
        "OutboundText": lambda **kwargs: SimpleNamespace(**kwargs),
        "carry": lambda: {},
    })
    case = {
        "id": "case-1", "channel": "asi1", "who": "user", "stage": "organized",
        "case_link_ready": True,
    }

    async def exercise():
        task = asyncio.create_task(env["reply"](
            None, case, "Document review complete", supersession_generation=1,
        ))
        await started.wait()
        watermark["case-1"] = 2
        release.set()
        await task

    asyncio.run(exercise())
    say.assert_not_awaited()


def test_inactive_reconciliation_clears_only_exact_pending_request_and_can_stay_silent():
    case = {
        "id": "case-1", "stage": "organizing", "stage_before_organizing": "booked",
        "after_care": None, "pending_after_care_id": "request-1",
        "pending_after_care_started_at": 600, "pending_after_care_target": ["asi1", "user"],
    }
    responses = Responses()
    responses.status = {"status": "inactive"}
    env = reconciliation_functions(case, responses)

    changed = asyncio.run(env["_reconcile_timed_out_operations"](
        None, case, now=1_000, deliver=False,
    ))

    assert changed is True and case["stage"] == "booked"
    assert not any(key.startswith("pending_after_care") for key in case)
    env["save"].assert_called_once_with(None, case)
    env["reply"].assert_not_awaited()
    assert [path for path, _ in responses] == ["/operations/status", "/operations/cancel"]


def test_new_location_care_request_suppresses_an_old_recovery_reply():
    from common.conversation import care_request, normalize_request

    env = coordinator_functions({"location_hint", "_turn_supersedes_recovered_reply"}, {
        "re": re,
        "normalize_request": normalize_request,
        "care_request": care_request,
        "QR_WORDS": ("visa qr", "clinic qr", "scan qr", "scan to pay", "payment qr"),
        "DONE_WORDS": ("they did", "gave me", "x-ray", "xray"),
    })
    case = {"stage": "organizing", "care_query": "old visit"}

    assert env["_turn_supersedes_recovered_reply"](
        case, "I twisted my ankle. Find care in Chicago, IL.",
    ) is True
    assert env["_turn_supersedes_recovered_reply"](case, "thanks") is False
    assert env["_turn_supersedes_recovered_reply"](
        case, "paid receipt", has_attachment=True,
    ) is True


def test_save_migrates_legacy_case_and_wallet_bearers_out_of_storage():
    class Storage:
        def __init__(self):
            self.values = {"case_ids": []}

        def get(self, key):
            return deepcopy(self.values.get(key))

        def set(self, key, value):
            self.values[key] = deepcopy(value)

    storage = Storage()
    env = coordinator_functions({"save"}, {
        "metric": Mock(), "case_hash": lambda value: f"hash-{value}",
    })
    case = {
        "id": "case-1", "stage": "organized", "_metric_stage": "organized",
        "visit_url": "https://www.getbillo.us/visit/private-bearer",
        "settlement": {
            "status": "handoff_ready",
            "handoff_url": "https://www.getbillo.us/wallet/private-bearer",
            "wallet_api_url": "https://api.getbillo.us/public/wallet/private-bearer",
        },
    }

    env["save"](SimpleNamespace(storage=storage), case)

    stored = storage.values["case:case-1"]
    assert stored["case_link_ready"] is True
    assert "visit_url" not in stored
    assert "handoff_url" not in stored["settlement"]
    assert "wallet_api_url" not in stored["settlement"]
    assert "private-bearer" not in repr(storage.values)


@pytest.mark.parametrize("case_id", ["", "unknown-keyed-case"])
def test_case_medic_never_guesses_a_patient_for_missing_or_unknown_case(case_id):
    load_case = Mock(return_value=None)
    env = coordinator_functions({"on_medic"}, {
        "ADDR": {"case_medic": "medic"},
        "load": load_case,
    })
    action = SimpleNamespace(case_id=case_id, action="retry_reader")

    asyncio.run(env["on_medic"](None, "medic", action))

    if case_id:
        load_case.assert_called_once_with(None, case_id)
    else:
        load_case.assert_not_called()
