"""Run: cd just && pytest -q tests   (no database, no keys needed)"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import TOKEN, app  # noqa: E402
from app import main  # noqa: E402

c = TestClient(app)
H = {"x-internal-token": TOKEN}


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


def test_red_flag_never_shops():
    import yaml
    rules = yaml.safe_load((ROOT / "rules" / "red_flags.yaml").read_text())["rules"]
    assert any("chest pain" in r["any"] for r in rules)


def test_guard_blocks_untrusted_link_and_over_limit():
    r = c.post("/guard/verify", json={"case_id": "t2", "npi": "1999999901", "amount": 900, "disputed_amount": 0,
                                      "mandate_max": 500, "pay_link": "https://evil-pay.example.com/x"}, headers=H).json()
    assert r["ok"] is False
    assert any("NOT trusted" in x for x in r["reasons"])
    assert any("over your limit" in x for x in r["reasons"])


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
    r = c.post("/visit-events", json={"case_id": "t4", "text": "They did an X-ray and gave me a splint"}, headers=H).json()
    assert r["total"] > 240


def test_after_care_paid_receipt_organizes_without_payment():
    case_id = "after-paid"
    c.post("/estimates", json={"case_id": case_id, "npi": "1999999901", "place": "Westwood", "amount": 240}, headers=H)
    c.post("/visit-events", json={"case_id": case_id, "text": "They did an X-ray"}, headers=H)
    bill = c.post("/reader/extract", json={"case_id": case_id, "demo": True}, headers=H).json()
    r = c.post("/after-care/organize", json={
        "case_id": case_id, "lines": bill["lines"], "hospital_npi": "1999999901", "payment_status": "paid",
    }, headers=H).json()
    assert r["payment_status"] == "paid"
    assert r["provider_match"] is True
    assert r["total"] == 2140.0
    assert r["estimate_difference"] == 1900.0
    assert r["visit_items_matched"] == 1
    assert any("No payment is needed" in step for step in r["next_steps"])


def test_after_care_unknown_status_cannot_imply_payment():
    bill = c.post("/reader/extract", json={"case_id": "unknown", "demo": True}, headers=H).json()
    r = c.post("/after-care/organize", json={"case_id": "unknown", "lines": bill["lines"]}, headers=H).json()
    assert r["payment_status"] == "unknown"
    assert any("Confirm whether" in step for step in r["next_steps"])


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
    r = c.post("/after-care/organize", json={
        "case_id": "no-provider", "lines": bill["lines"], "hospital_npi": "", "payment_status": "unpaid",
    }, headers=H).json()
    assert r["provider_match"] is False


def test_uploaded_bill_is_deleted_after_extraction(tmp_path, monkeypatch):
    upload = tmp_path / "bill.png"
    upload.write_bytes(b"private bill")
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    monkeypatch.setattr(main.reader, "read_bill", lambda *args: {"reader": "ocr", "lines": []})
    r = c.post("/reader/extract", json={"case_id": "t5", "file_url": "file:bill.png"}, headers=H)
    assert r.status_code == 200
    assert not upload.exists()
