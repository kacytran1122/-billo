"""ASI:One attachment ingestion and failure routing, with no network or uAgents startup."""
import ast
import asyncio
import base64
import re
import socket
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

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
    assert InboundText(handle_hash="synthetic", space_id="synthetic", text="").attachment_error == ""
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
    span = Mock()
    env = {
        "ack": AsyncMock(), "advertise_attachments": AsyncMock(), "upload_resources": AsyncMock(return_value=["file:synthetic.png"]),
        "AttachmentError": AttachmentError, "text_of": lambda msg: msg.text,
        "get_case": lambda *args: {"id": "synthetic", "stage": "new", "after_care": None},
        "case_scope": lambda *args, **kwargs: nullcontext(),
        "sentry_sdk": SimpleNamespace(start_transaction=Mock(return_value=nullcontext(span)),
                                      continue_trace=Mock(return_value=span), capture_message=Mock(),
                                      capture_exception=Mock(), set_tag=Mock()),
        "case_hash": lambda value: value, "METRIC_STAGES": {"new", "organized"},
        "first_matching_rule": lambda text, rules: {"say": "Emergency: call 911"} if "chest pain" in text else None,
        "SAFETY_RULES": [], "route_text": AsyncMock(), "say": AsyncMock(), "reply": AsyncMock(),
        "normalize_request": lambda value: value, "save": Mock(), "ADDR": {"bill_auditor": "test-auditor", "gateway": "test-gateway"},
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
    env["upload_resources"].assert_not_awaited()
    assert env["route_text"].await_args.args[-1] == []


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


@pytest.mark.parametrize("prior,restored", [(None, "new"), ({"total": 42}, "organized")])
def test_document_failure_restores_prior_stage_without_overwriting_existing_record(prior, restored):
    env = coordinator_functions({"on_result"})
    case = {"stage": "organizing", "after_care": prior}
    env["load"] = lambda *args: case
    result = SimpleNamespace(case_id="synthetic", ok=False, error="document_unreadable", total=0)
    asyncio.run(env["on_result"](None, "test-auditor", result))
    assert case["stage"] == restored
    assert case["after_care"] == prior
    response = env["reply"].await_args.args[2]
    assert "couldn’t reliably read" in response and "https://www.getbillo.us/tools/scan" in response
    assert "$0" not in response


def test_after_care_failure_from_unknown_sender_is_ignored():
    env = coordinator_functions({"on_result"})
    env["load"] = Mock()
    asyncio.run(env["on_result"](None, "untrusted-agent", SimpleNamespace(case_id="synthetic", ok=False)))
    env["load"].assert_not_called()
    env["reply"].assert_not_awaited()


@pytest.mark.parametrize("reader,expected", [
    ("ocr", "printed-total match is not guaranteed"),
    ("vision", "independent OCR verification may be unavailable"),
])
def test_organized_result_does_not_claim_unperformed_total_or_ocr_verification(reader, expected):
    env = coordinator_functions({"on_result"})
    case = {"stage": "organizing", "after_care": None}
    env["load"] = lambda *args: case
    env["photon_organized_bill"] = lambda **kwargs: "short review copy"
    result = SimpleNamespace(
        ok=True, case_id="synthetic", total=16, hospital_npi="", payment_status="paid", provider_match=False,
        estimate_amount=None, estimate_difference=None, reader=reader, unreviewed_lines=1,
        needs_review=[1], visit_items_matched=0, next_steps=[],
    )
    asyncio.run(env["on_result"](None, "test-auditor", result))
    detailed = env["reply"].await_args.args[2]
    assert expected in detailed
    assert "extracted charges matched the printed total" not in detailed
    assert "values were checked against the image" not in detailed


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


def test_bill_auditor_notifies_coordinator_when_reading_fails():
    sentry = SimpleNamespace(set_tag=Mock(), capture_message=Mock())
    env = functions("bill_auditor.py", {"on_after_care"}, {
        "case_span": lambda *args, **kwargs: nullcontext(), "sentry_sdk": sentry, "metric": Mock(),
        "organize_document": AsyncMock(side_effect=ValueError("private document text")),
        "AfterCareResult": lambda **kwargs: SimpleNamespace(**kwargs), "carry": lambda: {},
    })
    ctx = SimpleNamespace(send=AsyncMock())
    req = SimpleNamespace(case_id="synthetic", reply_to="test-coordinator", payment_status="unpaid")
    asyncio.run(env["on_after_care"](ctx, "test-sender", req))
    destination, result = ctx.send.await_args.args
    assert destination == "test-coordinator"
    assert result.ok is False and result.error == "document_unreadable"
    assert result.lines == [] and result.provider_match is False
    assert "private document text" not in str(sentry.capture_message.call_args)


def test_bill_auditor_preserves_uncoded_receipt_lines_in_organization():
    line = {"line_no": 1, "code": "", "description": "synthetic medicine", "units": 2, "charge": 16.0}
    calls = AsyncMock(side_effect=[
        {"lines": [line], "reader": "ocr", "needs_review": [1], "unreviewed_lines": [line]},
        {"total": 16.0, "provider_match": False, "visit_items_matched": 0, "next_steps": []},
    ])
    env = functions("bill_auditor.py", {"organize_document"}, {
        "core_post": calls, "task_span": lambda *args, **kwargs: nullcontext(Mock()), "metric": Mock(),
        "BillLine": lambda **kwargs: SimpleNamespace(**kwargs),
        "AfterCareResult": lambda **kwargs: SimpleNamespace(**kwargs), "carry": lambda: {},
    })
    req = SimpleNamespace(case_id="synthetic", file_url="file:synthetic.png", demo=False, hospital_npi="1999999901", payment_status="paid")
    result = asyncio.run(env["organize_document"](req))
    assert result.lines[0].code == "" and result.lines[0].charge == 16.0
    assert result.total == 16.0 and result.unreviewed_lines == 1 and result.needs_review == [1]
    assert calls.await_args_list[1].args[1]["lines"] == [line]
    # A care-plan NPI must not fill in an unreadable/missing NPI on the receipt.
    assert calls.await_args_list[1].args[1]["hospital_npi"] == ""
    assert result.hospital_npi == "" and result.provider_match is False


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
