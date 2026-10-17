"""Run: cd just && pytest -q tests   (no database, no keys needed)"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import TOKEN, app  # noqa: E402

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
