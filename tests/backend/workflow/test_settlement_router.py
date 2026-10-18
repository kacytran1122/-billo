"""Correlation contract for Settlement Router Core mutations."""
import ast
import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


ROOT = Path(__file__).resolve().parents[3]


def _route_function(env: dict):
    source = ROOT / "backend" / "fetch.ai" / "settlement_router.py"
    tree = ast.parse(source.read_text())
    names = {"_settlement_result", "_inactive_settlement_result", "route"}
    functions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    for function in functions:
        function.decorator_list = []
    future_annotations = ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0,
    )
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[future_annotations, *functions], type_ignores=[])),
            str(source),
            "exec",
        ),
        env,
    )
    return env["route"]


@pytest.mark.parametrize(("action", "expected_path"), [
    ("inspect_qr", "/visa/qr/inspect"),
    ("approve_qr", "/visa/qr/approve"),
    ("reimburse", "/visa/reimbursement/payout"),
])
def test_settlement_mutations_forward_request_id(action, expected_path):
    core_post = AsyncMock(side_effect=[{"status": "active"}, {"status": "ok"}])
    env = {
        "core_post": core_post,
        "SettlementResult": lambda **kwargs: SimpleNamespace(**kwargs),
        "carry": lambda: {},
        "case_span": lambda *args, **kwargs: nullcontext(),
        "check": lambda *args, **kwargs: nullcontext(),
        "task_span": lambda *args, **kwargs: nullcontext(),
        "metric": Mock(),
    }
    route = _route_function(env)
    ctx = SimpleNamespace(send=AsyncMock())
    request = SimpleNamespace(
        case_id="case-correlation", request_id="request-correlation", action=action,
        reply_to="coordinator", file_url="file:synthetic.png", demo=False,
        review_id="qrv_synthetic", benefit_name="HSA self-reimbursement", amount=100,
        benefit_approved=True, explicit_approval=True,
    )

    asyncio.run(route(ctx, "sender", request))

    status_path, status_payload = core_post.await_args_list[0].args
    path, payload = core_post.await_args_list[1].args
    assert status_path == "/operations/status"
    assert status_payload == {
        "case_id": request.case_id, "kind": "settlement", "request_id": request.request_id,
    }
    assert path == expected_path
    assert payload["request_id"] == request.request_id


@pytest.mark.parametrize("action", ["inspect_qr", "approve_qr", "reimburse"])
def test_settlement_completed_operation_replays_without_second_mutation(action):
    stored = {
        "status": "verified", "settlement_id": "qrv_replay", "trusted": True,
        "reasons": [], "merchant_name": "Synthetic Clinic", "amount": 100,
        "handoff_url": "https://www.getbillo.us/wallet/opaque", "mode": "simulate",
    }
    core_post = AsyncMock(return_value={
        "status": "completed", "action": action, "result": stored,
    })
    env = {
        "core_post": core_post,
        "SettlementResult": lambda **kwargs: SimpleNamespace(**kwargs),
        "carry": lambda: {}, "case_span": lambda *args, **kwargs: nullcontext(),
        "check": lambda *args, **kwargs: nullcontext(),
        "task_span": lambda *args, **kwargs: nullcontext(), "metric": Mock(),
    }
    route = _route_function(env)
    ctx = SimpleNamespace(send=AsyncMock())
    request = SimpleNamespace(
        case_id="case-replay", request_id="request-replay", action=action,
        reply_to="coordinator", file_url="file:already-consumed.png", demo=False,
        review_id="qrv_replay", benefit_name="HSA", amount=100,
        benefit_approved=True, explicit_approval=True,
    )

    asyncio.run(route(ctx, "sender", request))

    core_post.assert_awaited_once_with("/operations/status", {
        "case_id": request.case_id, "kind": "settlement", "request_id": request.request_id,
    })
    result = ctx.send.await_args.args[1]
    assert result.ok is True and result.action == action
    assert result.settlement_id == "qrv_replay" and result.amount == 100


def test_settlement_inactive_or_mismatched_operation_returns_safe_failure():
    for status in (
        {"status": "inactive"},
        {"status": "completed", "action": "approve_qr", "result": {"status": "ok"}},
    ):
        core_post = AsyncMock(return_value=status)
        env = {
            "core_post": core_post,
            "SettlementResult": lambda **kwargs: SimpleNamespace(
                status="", mode="", **kwargs,
            ),
            "carry": lambda: {}, "case_span": lambda *args, **kwargs: nullcontext(),
            "check": lambda *args, **kwargs: nullcontext(),
            "task_span": lambda *args, **kwargs: nullcontext(), "metric": Mock(),
        }
        route = _route_function(env)
        ctx = SimpleNamespace(send=AsyncMock())
        request = SimpleNamespace(
            case_id="case-inactive", request_id="request-inactive", action="inspect_qr",
            reply_to="coordinator", file_url="file:must-not-read.png", demo=False,
            review_id="", benefit_name="", amount=0,
            benefit_approved=False, explicit_approval=False,
        )

        asyncio.run(route(ctx, "sender", request))

        result = ctx.send.await_args.args[1]
        assert result.ok is False and result.error == "operation_inactive"
        core_post.assert_awaited_once()
