"""Exercise the real REST handler without starting a networked uAgent."""
import ast
import asyncio
from contextlib import nullcontext
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


ROOT = Path(__file__).resolve().parents[3]


class DeliveryStatus(Enum):
    DELIVERED = "delivered"
    FAILED = "failed"


def gateway_handler():
    tree = ast.parse((ROOT / "backend/fetch.ai/imessage_gateway.py").read_text())
    handler = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "from_bridge")
    handler.decorator_list = []
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    span = Mock()
    sentry = SimpleNamespace(
        continue_trace=Mock(return_value=span),
        start_transaction=Mock(return_value=nullcontext(span)),
        set_tag=Mock(), capture_message=Mock(),
    )
    env = {
        "ADDR": {"coordinator": "test-coordinator"},
        "INTERNAL_TOKEN": "test-only-token",
        "DeliveryStatus": DeliveryStatus,
        "Ack": lambda **kwargs: SimpleNamespace(**kwargs),
        "case_scope": lambda **kwargs: nullcontext(),
        "carry": lambda: {"sentry-trace": "test-updated-trace"},
        "sentry_sdk": sentry,
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, handler], type_ignores=[])), "imessage_gateway.py", "exec"), env)
    return env, sentry, span


def request():
    return SimpleNamespace(
        token="test-only-token", is_group=False, attachment_url="",
        trace={"sentry-trace": "test-inbound-trace"},
    )


def test_gateway_acknowledges_only_confirmed_coordinator_delivery():
    env, sentry, span = gateway_handler()
    ctx = SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(status=DeliveryStatus.DELIVERED)))
    req = request()

    result = asyncio.run(env["from_bridge"](ctx, req))

    assert result.ok is True
    ctx.send.assert_awaited_once_with("test-coordinator", req)
    assert req.token == ""
    assert req.trace == {"sentry-trace": "test-updated-trace"}
    sentry.capture_message.assert_not_called()
    span.set_status.assert_not_called()


@pytest.mark.parametrize("status", [DeliveryStatus.FAILED, None, "pending"])
def test_gateway_rejects_failed_or_unconfirmed_coordinator_delivery(status):
    env, sentry, span = gateway_handler()
    ctx = SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(status=status, detail="private diagnostic")))

    result = asyncio.run(env["from_bridge"](ctx, request()))

    assert result.ok is False
    assert result.detail == "Coordinator delivery failed"
    span.set_status.assert_called_once_with("internal_error")
    sentry.set_tag.assert_called_once_with("check", "workflow")
    sentry.capture_message.assert_called_once_with(
        "gateway could not deliver inbound message to coordinator", level="error"
    )
    assert "private diagnostic" not in str(sentry.capture_message.call_args)


def test_gateway_rejects_bad_token_without_sending():
    env, _, _ = gateway_handler()
    ctx = SimpleNamespace(send=AsyncMock())
    req = request()
    req.token = "wrong-token"

    result = asyncio.run(env["from_bridge"](ctx, req))

    assert result.ok is False
    assert result.detail == "bad token"
    ctx.send.assert_not_awaited()


def test_gateway_rejects_missing_coordinator_without_sending():
    env, _, _ = gateway_handler()
    env["ADDR"]["coordinator"] = ""
    ctx = SimpleNamespace(send=AsyncMock())

    result = asyncio.run(env["from_bridge"](ctx, request()))

    assert result.ok is False
    assert result.detail == "ADDR_COORDINATOR not set"
    ctx.send.assert_not_awaited()


def test_gateway_does_not_acknowledge_transport_exceptions():
    env, _, _ = gateway_handler()
    ctx = SimpleNamespace(send=AsyncMock(side_effect=TimeoutError("coordinator unavailable")))

    with pytest.raises(TimeoutError):
        asyncio.run(env["from_bridge"](ctx, request()))
