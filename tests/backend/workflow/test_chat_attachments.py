"""ASI:One attachment ingestion and failure routing, with no network or uAgents startup."""
import ast
import asyncio
import base64
import re
import socket
import sys
import time
from contextlib import asynccontextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/fetch.ai"))
from common import attachments
from common.attachments import AttachmentError, ChatAttachment, document_bytes


PNG = b"\x89PNG\r\n\x1a\nsynthetic-image"
PDF = b"%PDF-1.7\nsynthetic-document"


def functions(source, names, env):
    tree = ast.parse((ROOT / "backend/fetch.ai" / source).read_text())
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            nodes.append(node)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), source, "exec"), env)
    return env


class ResourceContent:
    def __init__(self, resource):
        self.resource = resource


class StartSessionContent:
    pass


def chat_functions():
    return functions("common/chat.py", {"resources_of", "upload_resources", "advertise_attachments"}, {
        "ResourceContent": ResourceContent, "StartSessionContent": StartSessionContent,
        "MetadataContent": lambda **kwargs: SimpleNamespace(**kwargs),
        "ChatMessage": lambda **kwargs: SimpleNamespace(**kwargs),
        "ChatAttachment": ChatAttachment, "AttachmentError": AttachmentError,
        "document_bytes": AsyncMock(return_value=(PNG, "image/png")),
        "core_upload": AsyncMock(return_value="file:synthetic.png"),
    })


def resource(resource_uri="https://files.example/receipt.png", **metadata):
    return SimpleNamespace(uri=resource_uri, metadata=metadata)


def message(*content):
    return SimpleNamespace(content=list(content))


def test_chat_uses_primary_document_not_thumbnail_as_a_second_bill():
    env = chat_functions()
    msg = message(ResourceContent([resource(), resource("https://files.example/thumb.png", role="thumbnail")]))
    assert env["resources_of"](msg) == [ChatAttachment("https://files.example/receipt.png")]


@pytest.mark.parametrize("key", ["url", "uri", "source", "image_url", "download_url", "file_url"])
def test_chat_finds_download_url_in_resource_metadata(key):
    env = chat_functions()
    msg = message(ResourceContent(resource("storage:opaque-id", **{key: "https://files.example/receipt.pdf", "mime_type": "application/pdf"})))
    assert env["resources_of"](msg) == [ChatAttachment("https://files.example/receipt.pdf", "application/pdf")]


@pytest.mark.parametrize("contents", [[], [resource("storage:opaque-id")], [resource("http://files.example/bill.png")]])
def test_chat_rejects_unreadable_or_insecure_resources_instead_of_dropping_them(contents):
    env = chat_functions()
    with pytest.raises(AttachmentError):
        env["resources_of"](message(ResourceContent(contents)))


def test_chat_uploads_document_bytes_to_core_and_returns_private_reference():
    env = chat_functions()
    result = asyncio.run(env["upload_resources"](message(ResourceContent(resource()))))
    assert result == ["file:synthetic.png"]
    env["document_bytes"].assert_awaited_once_with(ChatAttachment("https://files.example/receipt.png"))
    env["core_upload"].assert_awaited_once_with(PNG, "image/png")


def test_chat_rejects_multiple_primary_documents_before_downloading_any():
    env = chat_functions()
    with pytest.raises(AttachmentError, match="multiple_documents"):
        asyncio.run(env["upload_resources"](message(ResourceContent(resource()), ResourceContent(resource()))))
    env["document_bytes"].assert_not_awaited()
    env["core_upload"].assert_not_awaited()


def test_core_upload_failure_does_not_expose_original_private_error():
    env = chat_functions()
    env["core_upload"].side_effect = RuntimeError("private document https://secret.example/?token=sensitive")
    with pytest.raises(AttachmentError, match="^upload_failed$"):
        asyncio.run(env["upload_resources"](message(ResourceContent(resource()))))


def test_start_session_advertises_attachment_support_but_regular_messages_do_not():
    env = chat_functions()
    ctx = SimpleNamespace(send=AsyncMock())
    asyncio.run(env["advertise_attachments"](ctx, "test-user", message(StartSessionContent())))
    assert ctx.send.await_args.args[0] == "test-user"
    assert ctx.send.await_args.args[1].content[0].metadata == {"attachments": "true"}
    ctx.send.reset_mock()
    asyncio.run(env["advertise_attachments"](ctx, "test-user", message()))
    ctx.send.assert_not_awaited()


def test_installed_chatprotocol_models_support_resource_metadata_and_session_advertisement():
    protocol = pytest.importorskip("uagents_core.contrib.protocols.chat")
    from uuid import uuid4
    from common.chat import advertise_attachments, resources_of, text_of
    from common.models import AfterCareResult, InboundText

    msg = protocol.ChatMessage(content=[
        protocol.StartSessionContent(), protocol.TextContent(text="paid receipt"),
        protocol.ResourceContent(resource_id=uuid4(), resource=[
            protocol.Resource(uri="storage:opaque", metadata={"url": "https://files.example/receipt.pdf", "mime_type": "application/pdf"}),
            protocol.Resource(uri="https://files.example/thumb.png", metadata={"role": "thumbnail"}),
        ]),
    ])
    assert text_of(msg) == "paid receipt"
    assert resources_of(msg) == [ChatAttachment("https://files.example/receipt.pdf", "application/pdf")]
    ctx = SimpleNamespace(send=AsyncMock())
    asyncio.run(advertise_attachments(ctx, "test-user", msg))
    outgoing = ctx.send.await_args.args[1]
    assert isinstance(outgoing, protocol.ChatMessage)
    assert outgoing.timestamp is not None and outgoing.msg_id is not None
    assert outgoing.content[0].metadata == {"attachments": "true"}
    inbound = InboundText(handle_hash="synthetic", space_id="synthetic", text="")
    assert inbound.attachment_error == ""
    assert inbound.channel == "imessage" and inbound.handoff_claimed is False
    result = AfterCareResult(case_id="synthetic", lines=[], total=0, hospital_npi="", payment_status="unknown", provider_match=False)
    assert result.ok is True and result.error == ""


@pytest.mark.parametrize("mime,data", [("image/png", PNG), ("application/pdf", PDF), ("image/jpeg", b"\xff\xd8\xffsynthetic")])
def test_inline_documents_decode_and_verify_signature(mime, data):
    uri = f"data:{mime};base64,{base64.b64encode(data).decode()}"
    assert asyncio.run(document_bytes(ChatAttachment(uri))) == (data, mime)


@pytest.mark.parametrize("uri", [
    "data:image/png;base64,%%%", "data:image/png,not-base64", "data:text/html;base64,SGk=",
    "data:image/png;base64," + base64.b64encode(b"not-a-png").decode(),
    "data:image/jpeg;base64," + base64.b64encode(PNG).decode(),
])
def test_invalid_inline_documents_are_not_uploaded(uri):
    with pytest.raises(AttachmentError):
        asyncio.run(document_bytes(ChatAttachment(uri)))


def test_oversized_inline_encoding_rejected_before_base64_decode(monkeypatch):
    monkeypatch.setattr(attachments, "MAX_DOCUMENT_BYTES", 4)
    with patch.object(attachments.base64, "b64decode") as decode:
        with pytest.raises(AttachmentError, match="too_large"):
            asyncio.run(document_bytes(ChatAttachment("data:image/png;base64," + "a" * 150)))
        decode.assert_not_called()


@pytest.mark.parametrize("uri", [
    "http://8.8.8.8/document.png", "file:/etc/passwd", "https://user:password@8.8.8.8/a.png",
    "https://8.8.8.8:8443/a.png", "https://127.0.0.1/a.png", "https://169.254.169.254/latest/meta-data/",
    "https://10.0.0.1/a.png", "https://[::1]/a.png", "https://[::ffff:127.0.0.1]/a.png",
    "https://[2002:7f00:1::]/a.png", "https://224.0.0.1/a.png", "https://8.8.8.8/a.png#fragment",
    "https://[::127.0.0.1]/a.png", "https://[64:ff9b::a9fe:a9fe]/a.png", "https://[fec0::1]/a.png",
])
def test_download_rejects_local_metadata_insecure_and_credentialed_destinations(uri):
    with pytest.raises(AttachmentError):
        asyncio.run(attachments._pinned_destination(uri))


def test_mixed_public_private_dns_answers_are_rejected():
    async def exercise():
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ["8.8.8.8", "127.0.0.1"]]
        with patch.object(asyncio.get_running_loop(), "getaddrinfo", AsyncMock(return_value=answers)):
            with pytest.raises(AttachmentError, match="unsafe_destination"):
                await attachments._pinned_destination("https://files.example/bill.png")
    asyncio.run(exercise())


def remote_response(monkeypatch, response):
    requests, configurations = [], []

    class Transport:
        def __init__(self, **kwargs):
            configurations.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def handle_async_request(self, request):
            requests.append(request)
            return response

    monkeypatch.setattr(attachments.httpx, "AsyncHTTPTransport", Transport)
    return requests, configurations


def test_remote_download_pins_public_ip_keeps_tls_host_and_has_no_auth(monkeypatch):
    requests, configurations = remote_response(monkeypatch, httpx.Response(200, content=PNG, headers={"content-type": "application/octet-stream"}))

    async def exercise():
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        resolver = AsyncMock(return_value=answer)
        with patch.object(asyncio.get_running_loop(), "getaddrinfo", resolver):
            result = await document_bytes(ChatAttachment("https://files.example/receipt.png?signature=private"))
        assert result == (PNG, "image/png")
        resolver.assert_awaited_once()

    asyncio.run(exercise())
    assert requests[0].url.host == "8.8.8.8"
    assert requests[0].headers["host"] == "files.example"
    assert requests[0].extensions["sni_hostname"] == "files.example"
    assert "authorization" not in requests[0].headers
    assert "x-internal-token" not in requests[0].headers
    assert configurations == [{"retries": 0, "trust_env": False}]


@pytest.mark.parametrize("response", [
    httpx.Response(302, headers={"location": "https://127.0.0.1/private"}),
    httpx.Response(403, content=b"private provider error"),
    httpx.Response(200, content=b"<html>not a receipt</html>", headers={"content-type": "image/png"}),
    httpx.Response(200, content=PNG, headers={"content-length": str(11 * 1024 * 1024)}),
])
def test_remote_redirect_error_invalid_content_or_large_header_fails_closed(monkeypatch, response):
    requests, _ = remote_response(monkeypatch, response)
    with pytest.raises(AttachmentError):
        asyncio.run(document_bytes(ChatAttachment("https://8.8.8.8/document")))
    assert len(requests) == 1


def test_remote_stream_without_content_length_still_has_byte_limit(monkeypatch):
    monkeypatch.setattr(attachments, "MAX_DOCUMENT_BYTES", 8)
    remote_response(monkeypatch, httpx.Response(200, content=PNG))
    with pytest.raises(AttachmentError, match="too_large"):
        asyncio.run(document_bytes(ChatAttachment("https://8.8.8.8/document")))


def coordinator_functions(names):
    names = set(names) | {
        "_group_target_key", "_is_group_target", "_group_context",
        "_supersede_pending_operations", "_cancel_superseded_operations",
        "_recover_interrupted_operations", "new_case", "_priority_turn",
        "_on_imessage_turn", "_apply_after_care_result", "_apply_settlement_result",
    }
    span = Mock()

    @asynccontextmanager
    async def permit(*args, **kwargs):
        yield True

    env = {
        "asyncio": asyncio,
        "ack": AsyncMock(), "advertise_attachments": AsyncMock(), "upload_resources": AsyncMock(return_value=["file:synthetic.png"]),
        "AttachmentError": AttachmentError, "text_of": lambda msg: msg.text,
        "get_case": lambda *args: {"id": "synthetic", "stage": "new", "after_care": None},
        "load": lambda *args: None, "_key": lambda channel, who: f"door:{channel}:{who}",
        "_next_turn_sequence": lambda: 1,
        "_register_door_turn": lambda *args, **kwargs: 1, "_door_turn": permit,
        "_register_case_turn": lambda *args, **kwargs: 1, "_case_turn": permit,
        "_operation_state_lock": lambda *args: permit(),
        "_reload_case": lambda ctx, case: case,
        "_reconcile_timed_out_operations": AsyncMock(return_value=False),
        "_turn_supersedes_recovered_reply": lambda *args, **kwargs: False,
        "_record_superseding_ingress": lambda *args, **kwargs: "",
        "_associate_priority_case": lambda *args, **kwargs: None,
        "_abandon_door_turn": AsyncMock(), "_abandon_case_turn": AsyncMock(),
        "_current_turn_arrival": lambda case_id: 1,
        "_CASE_SUPERSEDING_USER_ARRIVALS": {},
        "_ACTIVE_RESULT_TURNS": {}, "_COMMITTED_RESULT_TURNS": set(),
        "_ACTIVE_FOLLOWUP_TURNS": {},
        "case_scope": lambda *args, **kwargs: nullcontext(),
        "sentry_sdk": SimpleNamespace(start_transaction=Mock(return_value=nullcontext(span)),
                                      continue_trace=Mock(return_value=span), capture_message=Mock(),
                                      capture_exception=Mock(), set_tag=Mock()),
        "case_hash": lambda value: value, "METRIC_STAGES": {"new", "organized"},
        "GROUP_PRIVATE_REPLY": "PRIVATE GROUP REDIRECT https://asi1.ai/ai/billo",
        "uuid4": uuid4, "time": time, "re": re, "OPERATION_TIMEOUT_SECONDS": 330,
        "first_matching_rule": lambda text, rules: {"say": "Emergency: call 911"} if "chest pain" in text else None,
        "SAFETY_RULES": [], "route_text": AsyncMock(), "say": AsyncMock(), "reply": AsyncMock(),
        "core_post": AsyncMock(return_value={"visit_url": "https://www.getbillo.us/visit/opaque-case-token"}),
        "normalize_request": lambda value: value, "save": Mock(), "ResourceContent": ResourceContent,
        "ADDR": {"bill_auditor": "test-auditor", "payment_guard": "test-payment", "gateway": "test-gateway"},
        "AfterCareRequest": lambda **kwargs: SimpleNamespace(**kwargs), "carry": lambda: {},
        "dump": lambda value: dict(vars(value)),
    }
    return functions("coordinator.py", names, env)


def test_actual_asi_chat_imports_attachment_before_routing():
    env = coordinator_functions({"on_chat"})
    asyncio.run(env["on_chat"](None, "test-user", SimpleNamespace(text="paid receipt")))
    assert env["route_text"].await_args.args[2:] == ("paid receipt", ["file:synthetic.png"])
    env["advertise_attachments"].assert_awaited_once()


def test_actual_asi_chat_prioritizes_emergency_before_document_download():
    env = coordinator_functions({"on_chat"})
    asyncio.run(env["on_chat"](None, "test-user", SimpleNamespace(text="I have chest pain, paid receipt")))
    env["advertise_attachments"].assert_not_awaited()
    env["upload_resources"].assert_not_awaited()
    assert env["route_text"].await_args.args[-1] == []


def test_failed_priority_ack_releases_both_door_and_case_queue_entries():
    env = coordinator_functions({"on_chat"})
    env["ack"].side_effect = RuntimeError("ack failed")
    env["_record_superseding_ingress"] = Mock(return_value="synthetic")

    with pytest.raises(RuntimeError, match="ack failed"):
        asyncio.run(env["on_chat"](
            None, "test-user", SimpleNamespace(text="I have chest pain"),
        ))

    env["_abandon_door_turn"].assert_awaited_once_with("door:asi1:test-user", 1)
    env["_abandon_case_turn"].assert_awaited_once_with("synthetic", 1)


def test_actual_asi_attachment_import_failure_is_not_a_care_search_or_demo():
    env = coordinator_functions({"on_chat"})
    env["upload_resources"].side_effect = AttachmentError("unsupported_uri")
    asyncio.run(env["on_chat"](None, "test-user", SimpleNamespace(text="hello, bill attached")))
    assert env["route_text"].await_args.kwargs == {"attachment_error": "unsupported_uri"}
    assert env["route_text"].await_args.args[-1] == []
    env["sentry_sdk"].capture_exception.assert_not_called()


@pytest.mark.parametrize("caption", ["approve clinic payment", "approve reimbursement $500", "hello", "find care near UCLA"])
def test_failed_attachment_cannot_become_an_approval_greeting_or_care_search(caption):
    env = coordinator_functions({"route_text"})
    asyncio.run(env["route_text"](None, {"stage": "new"}, caption, [], attachment_error="invalid"))
    response = env["reply"].await_args.args[2]
    assert "No charges were invented and no payment was approved" in response
    assert "/tools/scan" in response


def test_failed_attachment_with_emergency_caption_still_gets_emergency_help():
    env = coordinator_functions({"route_text"})
    case = {"stage": "new"}
    asyncio.run(env["route_text"](None, case, "chest pain", [], attachment_error="multiple"))
    assert case["stage"] == "emergency"
    assert env["reply"].await_args.args[2] == "Emergency: call 911"


def test_empty_photon_caption_with_attachment_error_is_not_silently_ignored():
    env = coordinator_functions({"on_imessage"})
    msg = SimpleNamespace(case_id="", space_id="synthetic", text="", attachment_url="", attachment_error="invalid", trace={}, is_group=False)
    asyncio.run(env["on_imessage"](None, "test-gateway", msg))
    assert env["route_text"].await_args.kwargs["attachment_error"] == "invalid"


def test_whatsapp_handoff_loads_existing_case_confirms_without_forwarding_code():
    env = coordinator_functions({"on_imessage"})
    case = {"id": "existing-case", "stage": "booked", "after_care": None}
    env["load"] = Mock(return_value=case)
    env["_key"] = lambda channel, who: f"door:{channel}:{who}"
    ctx = SimpleNamespace(storage=SimpleNamespace(set=Mock()))
    msg = SimpleNamespace(
        case_id="existing-case", handoff_claimed=True, channel="whatsapp_business",
        space_id="whatsapp_business:chat-1", text="", attachment_url="",
        attachment_error="", trace={}, is_group=False,
    )

    asyncio.run(env["on_imessage"](ctx, "test-gateway", msg))

    env["load"].assert_called_once_with(ctx, "existing-case")
    env["route_text"].assert_not_awaited()
    confirmation = env["reply"].await_args.args[2]
    assert "WhatsApp is now linked" in confirmation
    assert "BILLO-" not in confirmation
    assert case["last_target"] == ["whatsapp_business", "whatsapp_business:chat-1"]


def test_group_handoff_claim_never_loads_or_binds_the_private_case():
    env = coordinator_functions({"on_imessage"})
    env["load"] = Mock()
    env["get_case"] = Mock()
    storage = SimpleNamespace(get=Mock(return_value=None), set=Mock())
    ctx = SimpleNamespace(storage=storage)
    msg = SimpleNamespace(
        case_id="private-case", handoff_claimed=True, channel="whatsapp_business",
        space_id="whatsapp_business:group-1", text="", attachment_url="",
        attachment_error="", trace={}, is_group=True,
    )

    asyncio.run(env["on_imessage"](ctx, "test-gateway", msg))

    env["load"].assert_not_called()
    env["get_case"].assert_not_called()
    storage.set.assert_called_once_with(
        "group-target:whatsapp_business:whatsapp_business:group-1", True,
    )
    response = env["reply"].await_args
    assert response.args[1]["is_group"] is True
    assert response.args[1]["id"] != "private-case"
    assert response.args[2] == env["GROUP_PRIVATE_REPLY"]
    assert response.kwargs == {"group_safe": True}
    env["route_text"].assert_not_awaited()


@pytest.mark.parametrize("prior,restored", [(None, "new"), ({"total": 42}, "organized")])
def test_document_failure_restores_prior_stage_without_overwriting_existing_record(prior, restored):
    env = coordinator_functions({"on_result"})
    target = ["whatsapp_business", "whatsapp_business:chat-1"]
    case = {
        "stage": "organizing", "after_care": prior,
        "pending_after_care_id": "request-1", "pending_after_care_target": target,
    }
    env["load"] = lambda *args: case
    result = SimpleNamespace(
        case_id="synthetic", request_id="request-1",
        ok=False, error="document_unreadable", total=0,
    )
    asyncio.run(env["on_result"](None, "test-auditor", result))
    assert case["stage"] == restored
    assert case["after_care"] == prior
    response = env["reply"].await_args.args[2]
    assert "couldn’t reliably read" in response and "https://www.getbillo.us/tools/scan" in response
    assert "$0" not in response
    assert env["reply"].await_args.kwargs["target"] == target


def test_after_care_failure_from_unknown_sender_is_ignored():
    env = coordinator_functions({"on_result"})
    env["load"] = Mock()
    asyncio.run(env["on_result"](None, "untrusted-agent", SimpleNamespace(case_id="synthetic", ok=False)))
    env["load"].assert_not_called()
    env["reply"].assert_not_awaited()


def test_late_document_result_cannot_replace_a_newer_request():
    env = coordinator_functions({"on_result"})
    case = {
        "id": "synthetic", "stage": "choosing", "after_care": None,
        "pending_after_care_id": "new-request",
    }
    env["load"] = lambda *args: case
    stale = SimpleNamespace(case_id="synthetic", request_id="old-request", ok=True)

    asyncio.run(env["on_result"](None, "test-auditor", stale))

    assert case["stage"] == "choosing" and case["after_care"] is None
    assert case["pending_after_care_id"] == "new-request"
    env["reply"].assert_not_awaited()
    env["core_post"].assert_not_awaited()


def test_late_settlement_result_cannot_replace_a_newer_request():
    env = coordinator_functions({"on_settlement"})
    case = {
        "id": "synthetic", "stage": "organized", "settlement": None,
        "pending_settlement_id": "new-request",
    }
    env["load"] = lambda *args: case
    stale = SimpleNamespace(case_id="synthetic", request_id="old-request", ok=True)

    asyncio.run(env["on_settlement"](None, "test-payment", stale))

    assert case["settlement"] is None
    assert case["pending_settlement_id"] == "new-request"
    env["reply"].assert_not_awaited()


@pytest.mark.parametrize("reader,expected", [
    ("ocr", "printed-total match is not guaranteed"),
    ("vision", "independent OCR verification may be unavailable"),
])
def test_organized_result_does_not_claim_unperformed_total_or_ocr_verification(reader, expected):
    env = coordinator_functions({"on_result"})
    case = {
        "id": "synthetic", "stage": "organizing", "after_care": None,
        "pending_after_care_id": "request-1",
    }
    env["load"] = lambda *args: case
    env["photon_organized_bill"] = Mock(return_value="short review copy")
    result = SimpleNamespace(
        ok=True, case_id="synthetic", request_id="request-1",
        total=16, hospital_npi="", payment_status="paid", provider_match=False,
        estimate_amount=None, estimate_difference=None, reader=reader, unreviewed_lines=1,
        needs_review=[1], visit_items_matched=0, next_steps=[],
    )
    asyncio.run(env["on_result"](None, "test-auditor", result))
    detailed = env["reply"].await_args.args[2]
    assert expected in detailed
    assert "extracted charges matched the printed total" not in detailed
    assert "values were checked against the image" not in detailed
    env["core_post"].assert_awaited_once_with("/case-links", {"case_id": "synthetic"})
    assert case["case_link_ready"] is True and "visit_url" not in case
    assert env["photon_organized_bill"].call_args.kwargs["visit_url"] == (
        "https://www.getbillo.us/visit/opaque-case-token"
    )


def test_organized_result_reissues_case_url_without_storing_it_and_replies_to_upload_channel():
    env = coordinator_functions({"on_result"})
    visit_url = "https://www.getbillo.us/visit/existing-opaque-token"
    env["core_post"] = AsyncMock(return_value={"visit_url": visit_url})
    target = ["whatsapp_business", "whatsapp_business:chat-1"]
    case = {
        "id": "synthetic", "stage": "organizing", "after_care": None,
        "pending_after_care_id": "request-1",
        "pending_after_care_target": target,
    }
    env["load"] = lambda *args: case
    env["photon_organized_bill"] = Mock(return_value="short review copy")
    result = SimpleNamespace(
        ok=True, case_id="synthetic", request_id="request-1",
        total=16, hospital_npi="", payment_status="paid",
        provider_match=False, estimate_amount=None, estimate_difference=None, reader="ocr",
        unreviewed_lines=0, needs_review=[], visit_items_matched=0, next_steps=[],
    )

    asyncio.run(env["on_result"](None, "test-auditor", result))

    env["core_post"].assert_awaited_once_with("/case-links", {"case_id": "synthetic"})
    assert case["case_link_ready"] is True and "visit_url" not in case
    assert env["photon_organized_bill"].call_args.kwargs["visit_url"] == visit_url
    assert env["reply"].await_args.kwargs["target"] == target


def test_delayed_document_result_for_known_group_is_discarded_without_amount_or_case_link():
    env = coordinator_functions({"on_result"})
    target = ["whatsapp_business", "group-1"]
    case = {
        "id": "private-case", "stage": "organizing", "stage_before_organizing": "booked",
        "after_care": None, "pending_after_care_id": "request-1",
        "pending_after_care_target": target,
        "visit_url": "https://www.getbillo.us/visit/private-bearer",
    }
    env["load"] = lambda *args: case
    storage = SimpleNamespace(get=lambda key: key == "group-target:whatsapp_business:group-1")
    ctx = SimpleNamespace(storage=storage)
    result = SimpleNamespace(
        ok=True, case_id="private-case", request_id="request-1",
        total=987.65, hospital_npi="", payment_status="paid",
        provider_match=False, estimate_amount=400, estimate_difference=587.65, reader="ocr",
        unreviewed_lines=0, needs_review=[], visit_items_matched=0, next_steps=[],
    )

    asyncio.run(env["on_result"](ctx, "test-auditor", result))

    assert case["stage"] == "booked" and case["after_care"] is None
    assert "stage_before_organizing" not in case
    env["core_post"].assert_not_awaited()
    response = env["reply"].await_args
    assert response.args[2] == env["GROUP_PRIVATE_REPLY"]
    assert "$987.65" not in response.args[2] and "private-bearer" not in response.args[2]
    assert response.kwargs == {
        "target": target, "group_safe": True, "supersession_generation": 0,
    }


def test_delayed_settlement_result_for_known_group_is_discarded_without_amount_or_wallet_link():
    env = coordinator_functions({"on_settlement"})
    target = ["whatsapp_business", "group-1"]
    case = {
        "id": "private-case", "stage": "organized", "settlement": None,
        "pending_settlement_id": "request-1", "pending_settlement_target": target,
    }
    env["load"] = lambda *args: case
    storage = SimpleNamespace(get=lambda key: key == "group-target:whatsapp_business:group-1")
    ctx = SimpleNamespace(storage=storage)
    result = SimpleNamespace(
        case_id="private-case", request_id="request-1", ok=True, amount=987.65,
        handoff_url="https://www.getbillo.us/wallet/private-bearer",
    )

    asyncio.run(env["on_settlement"](ctx, "test-payment", result))

    assert case["settlement"] is None
    response = env["reply"].await_args
    assert response.args[2] == env["GROUP_PRIVATE_REPLY"]
    assert "$987.65" not in response.args[2] and "private-bearer" not in response.args[2]
    assert response.kwargs == {
        "target": target, "group_safe": True, "supersession_generation": 0,
    }


@pytest.mark.parametrize("stage,prior", [("organizing", None), ("organizing", {"total": 42}), ("organized", {"total": 42})])
def test_medic_requires_reupload_instead_of_replacing_real_document_with_empty_source_demo(stage, prior):
    env = coordinator_functions({"_apply_medic"})
    env["step_after_care"] = AsyncMock()
    case = {"stage": stage, "flags": {}, "after_care": prior}
    action = SimpleNamespace(action="retry_reader", patient_text="Retrying")
    asyncio.run(env["_apply_medic"](None, case, action))
    assert case["stage"] == ("organized" if prior else "new")
    assert case["after_care"] == prior
    env["step_after_care"].assert_not_awaited()
    assert "re-upload" in env["reply"].await_args.args[2]


def test_missing_document_does_not_implicitly_select_demo_extraction():
    env = coordinator_functions({"step_after_care"})
    case = {"stage": "new"}
    ctx = SimpleNamespace(send=AsyncMock())
    asyncio.run(env["step_after_care"](ctx, case, "", "unknown"))
    assert case["stage"] == "new"
    ctx.send.assert_not_awaited()
    assert "won’t substitute a demo document" in env["reply"].await_args.args[2]


def test_valid_document_upload_sends_progress_copy_with_keyword_only_photon_text():
    env = coordinator_functions({"step_after_care"})
    case = {"id": "synthetic", "stage": "new"}
    ctx = SimpleNamespace(agent=SimpleNamespace(address="coordinator"), send=AsyncMock())

    asyncio.run(env["step_after_care"](ctx, case, "file:synthetic.png", "paid"))

    progress = env["reply"].await_args
    assert len(progress.args) == 3
    assert progress.args[2].startswith("Document received")
    assert progress.kwargs == {
        "photon_text": "📸 Got it — reading your bill.\nChecking provider, charges + saved estimate.",
    }
    assert case["stage"] == "organizing"
    request = ctx.send.await_args.args[1]
    assert request.file_url == "file:synthetic.png"
    assert request.payment_status == "paid"
    assert request.request_id == case["pending_after_care_id"]
    env["core_post"].assert_awaited_once_with("/operations/start", {
        "case_id": "synthetic", "kind": "after_care", "request_id": request.request_id,
    })
    assert 0 <= time.time() - case["pending_after_care_started_at"] < 5


def test_only_legacy_uncorrelated_operation_is_restored_synchronously():
    env = coordinator_functions(set())
    recover = env["_recover_interrupted_operations"]

    legacy = {
        "stage": "organizing", "stage_before_organizing": "booked", "after_care": None,
    }
    assert recover(legacy, now=1_000) is True
    assert legacy["stage"] == "booked" and "stage_before_organizing" not in legacy

    timed_out = {
        "stage": "organizing", "after_care": {"total": 42},
        "pending_after_care_id": "request-1", "pending_after_care_started_at": 600,
        "pending_settlement_id": "request-2", "pending_settlement_started_at": 699,
    }
    assert recover(timed_out, now=1_000) is False
    assert timed_out["stage"] == "organizing"
    assert timed_out["pending_after_care_id"] == "request-1"
    assert timed_out["pending_settlement_id"] == "request-2"


def test_bill_auditor_notifies_coordinator_when_reading_fails():
    sentry = SimpleNamespace(set_tag=Mock(), capture_message=Mock())
    env = functions("bill_auditor.py", {"on_after_care"}, {
        "case_span": lambda *args, **kwargs: nullcontext(), "sentry_sdk": sentry, "metric": Mock(),
        "organize_document": AsyncMock(side_effect=ValueError("private document text")),
        "AfterCareResult": lambda **kwargs: SimpleNamespace(**kwargs), "carry": lambda: {},
    })
    ctx = SimpleNamespace(send=AsyncMock())
    req = SimpleNamespace(
        case_id="synthetic", request_id="request-1",
        reply_to="test-coordinator", payment_status="unpaid",
    )
    asyncio.run(env["on_after_care"](ctx, "test-sender", req))
    destination, result = ctx.send.await_args.args
    assert destination == "test-coordinator"
    assert result.ok is False and result.error == "document_unreadable"
    assert result.lines == [] and result.provider_match is False
    assert result.request_id == "request-1"
    assert "private document text" not in str(sentry.capture_message.call_args)


def test_bill_auditor_preserves_uncoded_receipt_lines_in_organization():
    line = {"line_no": 1, "code": "", "description": "synthetic medicine", "units": 2, "charge": 16.0}
    calls = AsyncMock(side_effect=[
        {"status": "active"},
        {"lines": [line], "reader": "ocr", "document_type": "receipt",
         "needs_review": [1], "unreviewed_lines": [line],
         "fallback_reason": "low OCR confidence"},
        {
            "lines": [line], "total": 16.0, "hospital_npi": "",
            "payment_status": "paid", "provider_match": False,
            "visit_items_matched": 0, "next_steps": [], "reader": "ocr",
            "needs_review": [1], "unreviewed_lines": [1],
            "fallback_reason": "low OCR confidence",
        },
    ])
    env = functions("bill_auditor.py", {
        "_after_care_result", "_inactive_after_care_result", "organize_document",
    }, {
        "core_post": calls, "task_span": lambda *args, **kwargs: nullcontext(Mock()), "metric": Mock(),
        "BillLine": lambda **kwargs: SimpleNamespace(**kwargs),
        "AfterCareResult": lambda **kwargs: SimpleNamespace(**kwargs), "carry": lambda: {},
    })
    req = SimpleNamespace(
        case_id="synthetic", request_id="request-1", file_url="file:synthetic.png",
        demo=False, hospital_npi="1999999901", payment_status="paid",
    )
    result = asyncio.run(env["organize_document"](req))
    assert result.lines[0].code == "" and result.lines[0].charge == 16.0
    assert result.total == 16.0 and result.unreviewed_lines == 1 and result.needs_review == [1]
    assert calls.await_args_list[2].args[1]["lines"] == [line]
    # A care-plan NPI must not fill in an unreadable/missing NPI on the receipt.
    assert calls.await_args_list[2].args[1]["hospital_npi"] == ""
    assert calls.await_args_list[2].args[1]["reader"] == "ocr"
    assert calls.await_args_list[2].args[1]["document_type"] == "receipt"
    assert calls.await_args_list[2].args[1]["needs_review"] == [1]
    assert calls.await_args_list[2].args[1]["unreviewed_lines"] == [1]
    assert calls.await_args_list[2].args[1]["fallback_reason"] == "low OCR confidence"
    assert result.hospital_npi == "" and result.provider_match is False
    assert result.request_id == "request-1"


def test_core_reader_has_longer_timeout_and_upload_uses_internal_auth_only_to_core():
    requests = []

    class Client:
        async def post(self, path, **kwargs):
            requests.append((path, kwargs))
            return httpx.Response(200, request=httpx.Request("POST", "https://core.test" + path),
                                  json={"file_url": "file:synthetic.png"})

    env = functions("common/core.py", {"core_post", "core_upload"}, {
        "client": AsyncMock(return_value=Client()), "_HEADERS": {"x-internal-token": "test-only"},
        "carry": lambda: {"sentry-trace": "test-trace"}, "re": re,
    })
    asyncio.run(env["core_post"]("/reader/extract", {"file_url": "file:synthetic.png"}))
    assert asyncio.run(env["core_upload"](PNG, "image/png")) == "file:synthetic.png"
    assert requests[0][1]["timeout"] == 90
    assert requests[1][0] == "/files" and requests[1][1]["content"] == PNG
    assert requests[1][1]["headers"]["content-type"] == "image/png"
    assert requests[1][1]["headers"]["x-internal-token"] == "test-only"
