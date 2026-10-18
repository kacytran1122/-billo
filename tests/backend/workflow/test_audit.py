"""Run from the repository root with pytest -q tests/backend."""
import ast
import asyncio
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "api"))
# Unit tests must be deterministic even when the developer's local .env points
# at production-like services. load_dotenv() will not override these values.
os.environ["BILLO_MODE"] = "demo"
os.environ["DATABASE_URL"] = ""
os.environ["SENTRY_DSN"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.main import TOKEN, app  # noqa: E402
from app import main  # noqa: E402

c = TestClient(app)
H = {"x-internal-token": TOKEN}


def _start_operation(case_id: str, kind: str) -> str:
    request_id = uuid4().hex
    response = c.post("/operations/start", json={
        "case_id": case_id, "kind": kind, "request_id": request_id,
    }, headers=H)
    assert response.status_code == 200
    return request_id


def _fetch_functions(source: str, names: set[str], env: dict):
    tree = ast.parse((ROOT / "backend" / "fetch.ai" / source).read_text())
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), source, "exec"), env)
    return env


def run_demo_audit(case_id="t1"):
    c.post("/estimates", json={"case_id": case_id, "npi": "1999999901", "place": "Westwood", "amount": 240}, headers=H)
    bill = c.post("/reader/extract", json={"case_id": case_id, "demo": True}, headers=H).json()
    flags = []
    for line in bill["lines"]:
        r = c.post("/audit/line", json={"case_id": case_id, "line": line, "all_lines": bill["lines"]}, headers=H).json()
        if r["flag"]:
            flags.append(r["flag"])
    total = c.post("/audit/total", json={"case_id": case_id, "lines": bill["lines"], "line_flags": flags}, headers=H).json()
    return bill, flags + total["flags"], total


def test_demo_bill_has_the_three_expected_flags():
    bill, flags, total = run_demo_audit()
    assert bill["reader"] == "demo"
    kinds = {(f["rule_id"], f["kind"]) for f in flags}
    assert ("DUP-001", "dispute") in kinds          # X-ray charged twice: both checks agree
    assert ("PRICE-P90", "ask_hospital") in kinds    # splint: only the price check -> verifier rejects the dispute
    assert ("GFE-400", "dispute") in kinds           # $1,900 over the $240 Good Faith Estimate
    assert len(flags) == 3
    assert total["disputed_amount"] == 1900.0        # pay the estimate, dispute the rest


def test_audit_pricing_uses_saved_region_and_kind_for_lines_and_total(monkeypatch):
    case_id = "chicago-er-audit-context"
    c.post("/estimates", json={
        "case_id": case_id,
        "npi": "custom-provider",
        "place": "Selected emergency department",
        "amount": 100,
        "region": "chicago",
        "kind": "er",
    }, headers=H)
    calls = []

    def local_stats(code, region="los-angeles", include_er=False):
        calls.append((code, region, include_er))
        return {"p10": 90, "p50": 100, "p90": 110, "n": 20, "source": "test"}

    monkeypatch.setattr(main.store, "price_stats", local_stats)
    line = {
        "line_no": 1, "code": "73560", "description": "Knee X-ray",
        "charge": 600, "service_date": "2026-10-18",
    }
    checked = c.post(
        "/audit/line",
        json={"case_id": case_id, "line": line, "all_lines": [line]},
        headers=H,
    ).json()
    assert checked["stats"]["p50"] == 100
    total = c.post(
        "/audit/total",
        json={"case_id": case_id, "lines": [line], "line_flags": []},
        headers=H,
    ).json()
    assert total["flags"][0]["rule_id"] == "GFE-400"
    assert calls == [
        ("73560", "chicago", True),
        ("73560", "chicago", True),
    ]
    assert "california" not in total["charity_care_hint"].lower()
    assert "financial-assistance policy" in total["charity_care_hint"].lower()
    assert "vary by provider and location" in total["charity_care_hint"].lower()


def test_audit_without_saved_location_never_falls_back_to_los_angeles(monkeypatch):
    calls = []

    def unexpected_stats(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("price_stats must not run without a saved region and kind")

    monkeypatch.setattr(main.store, "price_stats", unexpected_stats)
    line = {
        "line_no": 1, "code": "73560", "description": "Knee X-ray",
        "charge": 900, "service_date": "2026-10-18",
    }
    checked = c.post(
        "/audit/line",
        json={"case_id": "document-only-audit", "line": line, "all_lines": [line]},
        headers=H,
    ).json()
    assert checked["stats"] is None
    assert checked["flag"] is None
    total = c.post(
        "/audit/total",
        json={"case_id": "document-only-audit", "lines": [line], "line_flags": []},
        headers=H,
    ).json()
    assert total["flags"] == []
    assert total["disputed_amount"] == 0
    assert calls == []


def test_red_flag_never_shops():
    import yaml
    rules = yaml.safe_load((ROOT / "backend" / "rules" / "red_flags.yaml").read_text())["rules"]
    assert any("chest pain" in r["any"] for r in rules)


def test_qr_link_flow():
    link = c.post("/link-codes", json={"case_id": "t3"}, headers=H).json()
    assert c.get(f"/api/link/{link['code']}").json()["status"] == "waiting"
    a = c.post("/link/claim", json={"code": link["code"], "handle_hash": "h1", "space_id": "s1"}, headers=H).json()
    b = c.post("/link/claim", json={"code": link["code"], "handle_hash": "h1", "space_id": "s1"}, headers=H).json()
    assert a["status"] == b["status"] == "linked" and a["case_id"] == "t3"  # idempotent
    c.post("/link/stop", json={"handle_hash": "h1"}, headers=H)
    assert c.get("/reminders/allowed", params={"case_id": "t3"}, headers=H).json()["ok"] is False


def test_live_visit_log_running_total():
    c.post("/estimates", json={"case_id": "t4", "npi": "1999999901", "place": "Westwood", "amount": 240}, headers=H)
    r = c.post("/visit-events", json={"case_id": "t4", "text": "The bill lists 73560 and L1830"}, headers=H).json()
    assert r["total"] > 240
    assert "matched service item(s)" in r["say"]
    assert "not a final provider quote" in r["say"]


def test_coordinator_handles_stop_and_repeats_valid_booking_choices():
    source = (ROOT / "backend" / "fetch.ai" / "coordinator.py").read_text()
    assert 'if low == "stop"' in source
    assert 'case["followup_due"] = 0' in source
    assert 'case.get("stopped")' in source
    assert "That option number isn’t available" in source


def test_after_care_paid_receipt_organizes_without_payment():
    case_id = "after-paid"
    c.post("/estimates", json={"case_id": case_id, "npi": "1999999901", "place": "Westwood", "amount": 240}, headers=H)
    c.post("/visit-events", json={"case_id": case_id, "text": "They did an X-ray"}, headers=H)
    bill = c.post("/reader/extract", json={"case_id": case_id, "demo": True}, headers=H).json()
    request_id = _start_operation(case_id, "after_care")
    r = c.post("/after-care/organize", json={
        "case_id": case_id, "request_id": request_id, "lines": bill["lines"],
        "hospital_npi": "1999999901", "payment_status": "paid",
    }, headers=H).json()
    assert r["payment_status"] == "paid"
    assert r["provider_match"] is True
    assert r["total"] == 2140.0
    assert r["estimate_difference"] == 1900.0
    assert r["visit_items_matched"] == 1
    assert any("No payment is needed" in step for step in r["next_steps"])


def test_after_care_unknown_status_cannot_imply_payment():
    bill = c.post("/reader/extract", json={"case_id": "unknown", "demo": True}, headers=H).json()
    request_id = _start_operation("unknown", "after_care")
    r = c.post("/after-care/organize", json={
        "case_id": "unknown", "request_id": request_id, "lines": bill["lines"],
    }, headers=H).json()
    assert r["payment_status"] == "unknown"
    assert any("Confirm whether" in step for step in r["next_steps"])


def test_bill_auditor_forwards_request_id_only_to_organization_mutation():
    line = {
        "line_no": 1, "code": "73560", "description": "Synthetic X-ray",
        "units": 1, "charge": 100.0,
    }
    core_post = AsyncMock(side_effect=[
        {"status": "active"},
        {"lines": [line], "reader": "ocr", "needs_review": [], "unreviewed_lines": []},
        {
            "lines": [line], "total": 100.0, "hospital_npi": "",
            "payment_status": "unpaid", "provider_match": False,
            "visit_items_matched": 0, "next_steps": [], "reader": "ocr",
            "needs_review": [], "unreviewed_lines": [],
        },
    ])
    env = {
        "core_post": core_post,
        "task_span": lambda *args, **kwargs: nullcontext(Mock()),
        "metric": Mock(),
        "BillLine": lambda **kwargs: SimpleNamespace(**kwargs),
        "AfterCareResult": lambda **kwargs: SimpleNamespace(**kwargs),
        "carry": lambda: {},
    }
    functions = _fetch_functions(
        "bill_auditor.py",
        {"_after_care_result", "_inactive_after_care_result", "organize_document"},
        env,
    )
    request = SimpleNamespace(
        case_id="case-correlation", request_id="request-correlation",
        file_url="file:synthetic.png", demo=False, payment_status="unpaid",
    )

    asyncio.run(functions["organize_document"](request))

    status_path, status_payload = core_post.await_args_list[0].args
    extraction_payload = core_post.await_args_list[1].args[1]
    organization_payload = core_post.await_args_list[2].args[1]
    assert status_path == "/operations/status"
    assert status_payload == {
        "case_id": request.case_id, "kind": "after_care", "request_id": request.request_id,
    }
    assert "request_id" not in extraction_payload
    assert organization_payload["request_id"] == request.request_id


def test_bill_auditor_replays_completed_result_without_ocr_or_mutation():
    stored = {
        "lines": [{
            "line_no": 1, "code": "73560", "description": "must not be replayed",
            "units": 1, "charge": 100.0,
        }],
        "total": 100.0, "hospital_npi": "1999999901", "payment_status": "paid",
        "provider_match": True, "estimate_amount": 90.0, "estimate_difference": 10.0,
        "visit_items_matched": 1, "next_steps": ["Keep the record."], "reader": "ocr",
        "needs_review": [1], "unreviewed_lines": 1, "fallback_reason": "",
    }
    core_post = AsyncMock(return_value={
        "status": "completed", "action": "after_care", "result": stored,
    })
    env = {
        "core_post": core_post,
        "task_span": lambda *args, **kwargs: nullcontext(Mock()), "metric": Mock(),
        "BillLine": lambda **kwargs: SimpleNamespace(**kwargs),
        "AfterCareResult": lambda **kwargs: SimpleNamespace(**kwargs), "carry": lambda: {},
    }
    functions = _fetch_functions(
        "bill_auditor.py",
        {"_after_care_result", "_inactive_after_care_result", "organize_document"},
        env,
    )
    request = SimpleNamespace(
        case_id="case-replay", request_id="request-replay",
        file_url="file:already-consumed.png", demo=False, payment_status="unknown",
    )

    result = asyncio.run(functions["organize_document"](request))

    core_post.assert_awaited_once_with("/operations/status", {
        "case_id": request.case_id, "kind": "after_care", "request_id": request.request_id,
    })
    assert result.total == 100.0 and result.payment_status == "paid"
    assert result.lines == [] and result.needs_review == [1]
    assert "must not be replayed" not in repr(result)
    assert result.unreviewed_lines == 1 and result.request_id == request.request_id


def test_bill_auditor_returns_safe_failure_for_inactive_operation():
    core_post = AsyncMock(return_value={"status": "inactive"})
    env = {
        "core_post": core_post,
        "task_span": lambda *args, **kwargs: nullcontext(Mock()), "metric": Mock(),
        "BillLine": lambda **kwargs: SimpleNamespace(**kwargs),
        "AfterCareResult": lambda **kwargs: SimpleNamespace(**kwargs), "carry": lambda: {},
    }
    functions = _fetch_functions(
        "bill_auditor.py",
        {"_after_care_result", "_inactive_after_care_result", "organize_document"},
        env,
    )
    request = SimpleNamespace(
        case_id="case-inactive", request_id="request-inactive",
        file_url="file:must-not-read.png", demo=False, payment_status="unpaid",
    )

    result = asyncio.run(functions["organize_document"](request))

    assert result.ok is False and result.error == "operation_inactive"
    assert result.lines == [] and result.request_id == request.request_id
    core_post.assert_awaited_once()


def test_benefits_require_a_named_coverage_source():
    none = c.post("/benefits/check", json={"case_id": "benefits", "text": "Can I get money back?"}, headers=H).json()
    assert none["paths"] == []
    named = c.post("/benefits/check", json={"case_id": "benefits", "text": "I have an HSA and an out-of-network PPO"}, headers=H).json()
    assert {p["name"] for p in named["paths"]} == {"HSA self-reimbursement", "Out-of-network insurance claim"}
    assert all(p["status"] == "possible_not_confirmed" for p in named["paths"])
    false_positive = c.post("/benefits/check", json={"case_id": "benefits", "text": "I need support"}, headers=H).json()
    assert false_positive["paths"] == []


def test_after_care_requires_a_provider_for_a_match():
    bill = c.post("/reader/extract", json={"case_id": "no-provider", "demo": True}, headers=H).json()
    request_id = _start_operation("no-provider", "after_care")
    r = c.post("/after-care/organize", json={
        "case_id": "no-provider", "request_id": request_id, "lines": bill["lines"],
        "hospital_npi": "", "payment_status": "unpaid",
    }, headers=H).json()
    assert r["provider_match"] is False


def _unpaid_case(case_id="visa-unpaid"):
    c.post("/estimates", json={"case_id": case_id, "npi": "1999999901", "place": "Westwood Urgent Care", "amount": 240}, headers=H)
    bill = c.post("/reader/extract", json={"case_id": case_id, "demo": True}, headers=H).json()
    request_id = _start_operation(case_id, "after_care")
    c.post("/after-care/organize", json={
        "case_id": case_id, "request_id": request_id, "lines": bill["lines"],
        "hospital_npi": "1999999901", "payment_status": "unpaid",
    }, headers=H)


def test_visa_qr_requires_review_then_explicit_approval():
    case_id = "visa-qr-good"
    _unpaid_case(case_id)
    inspect_request = _start_operation(case_id, "settlement")
    review = c.post("/visa/qr/inspect", json={
        "case_id": case_id, "request_id": inspect_request, "demo": True,
    }, headers=H).json()
    assert review["trusted"] is True
    approve_request = _start_operation(case_id, "settlement")
    denied = c.post("/visa/qr/approve", json={
        "case_id": case_id, "request_id": approve_request,
        "review_id": review["settlement_id"],
    }, headers=H)
    assert denied.status_code == 409
    approved = c.post("/visa/qr/approve", json={
        "case_id": case_id, "request_id": approve_request,
        "review_id": review["settlement_id"], "explicit_approval": True,
    }, headers=H).json()
    assert approved["status"] == "handoff_ready"
    assert "/wallet/" in approved["handoff_url"]
    assert "/public/wallet/" in approved["wallet_api_url"]


def test_visa_qr_rejects_tampering_and_wrong_provider():
    from app import visa
    payload = visa.demo_qr("Other Clinic", 2140, "BILLO-X")
    result = visa.inspect_qr(payload, "Westwood Urgent Care", 2140, expected_invoice="BILLO-X")
    assert result["trusted"] is False
    assert any("merchant name" in reason for reason in result["reasons"])
    tampered = payload.replace("2140.00", "2141.00")
    result = visa.inspect_qr(tampered, "Other Clinic", 2141, expected_invoice="BILLO-X")
    assert result["trusted"] is False
    assert any("checksum" in reason for reason in result["reasons"])


def test_visa_qr_rejects_empty_and_trivial_merchant_matches():
    from app import visa

    payload = visa.demo_qr("Westwood Urgent Care", 240, "BILLO-X")
    for expected_provider in ("", "A", "Urgent Care"):
        result = visa.inspect_qr(payload, expected_provider, 240, expected_invoice="BILLO-X")
        assert result["trusted"] is False
        assert "merchant name does not match the care provider" in result["reasons"]

    generic_payload = visa.demo_qr("Urgent Care", 240, "BILLO-X")
    generic_result = visa.inspect_qr(
        generic_payload, "Urgent Care", 240, expected_invoice="BILLO-X"
    )
    assert generic_result["trusted"] is False
    assert visa._merchant_name_matches("Westwood Urgent Care", "") is False


def test_visa_qr_accepts_specific_provider_name_variants():
    from app import visa

    punctuation = visa.demo_qr("ST MARYS CLINIC", 240, "BILLO-X")
    assert visa.inspect_qr(
        punctuation, "St. Mary's Clinic", 240, expected_invoice="BILLO-X"
    )["trusted"] is True

    suffix = visa.demo_qr("Westwood Urgent Care Demo", 240, "BILLO-X")
    assert visa.inspect_qr(
        suffix, "Westwood Urgent Care", 240, expected_invoice="BILLO-X"
    )["trusted"] is True


def test_reimbursement_requires_paid_receipt_checked_benefit_and_approvals():
    case_id = "visa-reimburse"
    c.post("/estimates", json={"case_id": case_id, "npi": "1999999901", "place": "Westwood", "amount": 240}, headers=H)
    bill = c.post("/reader/extract", json={"case_id": case_id, "demo": True}, headers=H).json()
    after_request = _start_operation(case_id, "after_care")
    c.post("/after-care/organize", json={
        "case_id": case_id, "request_id": after_request, "lines": bill["lines"],
        "hospital_npi": "1999999901", "payment_status": "paid",
    }, headers=H)
    c.post("/benefits/check", json={"case_id": case_id, "text": "I have an HSA"}, headers=H)
    payout_request = _start_operation(case_id, "settlement")
    denied = c.post("/visa/reimbursement/payout", json={
        "case_id": case_id, "request_id": payout_request,
        "benefit_name": "HSA self-reimbursement", "amount": 120,
        "benefit_approved": True,
    }, headers=H)
    assert denied.status_code == 409
    paid = c.post("/visa/reimbursement/payout", json={
        "case_id": case_id, "request_id": payout_request,
        "benefit_name": "HSA self-reimbursement", "amount": 120,
        "benefit_approved": True, "explicit_patient_approval": True,
    }, headers=H).json()
    assert paid["status"] == "simulated_paid"
    assert paid["amount"] == 120


def test_uploaded_bill_is_deleted_after_extraction(tmp_path, monkeypatch):
    upload = tmp_path / "bill.png"
    upload.write_bytes(b"private bill")
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    monkeypatch.setattr(main.reader, "read_bill", lambda *args: {"reader": "ocr", "lines": []})
    r = c.post("/reader/extract", json={"case_id": "t5", "file_url": "file:bill.png"}, headers=H)
    assert r.status_code == 200
    assert not upload.exists()


def test_orphaned_upload_cleanup_is_bounded_to_old_billo_files(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    monkeypatch.setattr(main, "UPLOAD_RETENTION_SECONDS", 900)
    old = tmp_path / ("a" * 32 + ".png")
    recent = tmp_path / ("b" * 32 + ".pdf")
    unrelated = tmp_path / "keep-me.txt"
    for path in (old, recent, unrelated):
        path.write_bytes(b"synthetic")
    os.utime(old, (100, 100))
    os.utime(recent, (1500, 1500))
    os.utime(unrelated, (100, 100))

    assert main.cleanup_orphaned_uploads(now=2000) == 1
    assert not old.exists()
    assert recent.exists() and unrelated.exists()
