"""Tests for the OCR bill reader. Run from the repo root: pytest ocr/tests -q"""
import json
from pathlib import Path

import pytest

from ocr import engine, reader
from ocr.engine import Box
from ocr.parse import group_rows, parse_bill, parse_row
from ocr.verify import verify_lines

FIX = Path(__file__).parent / "fixtures" / "synthetic_bill.png"


def row(*cells, y=100, conf=0.9):
    """Fake one OCR row: cells laid out left to right."""
    return [Box(t, 100 * i, y, 100 * i + 80, y + 30, conf) for i, t in enumerate(cells)]


# ---- parsing ---------------------------------------------------------------

def test_parse_full_row():
    l = parse_row(row("09/14/2026", "0300", "85025", "CBC W/ AUTO DIFF", "1", "$84.00", "$84.00"))
    assert (l["code"], l["rev_code"], l["service_date"], l["units"], l["charge"]) == \
        ("85025", "0300", "2026-09-14", 1, 84.0)
    assert l["description"] == "CBC W/ AUTO DIFF"


def test_units_from_unit_price_times_total_even_without_qty_box():
    l = parse_row(row("J1885", "KETOROLAC INJ", "$38.50", "$77.00"))
    assert l["units"] == 2 and l["charge"] == 77.0


def test_digit_inside_description_is_not_units():
    l = parse_row(row("99284", "ER VISIT LEVEL 4", "$2,450.00", "$2,450.00"))
    assert l["units"] == 1 and l["description"] == "ER VISIT LEVEL 4"


def test_hcpcs_with_modifier():
    l = parse_row(row("J1885-JW", "KETOROLAC WASTE", "$12.00"))
    assert (l["code"], l["modifier"]) == ("J1885", "JW")


@pytest.mark.parametrize("text", ["TOTAL CHARGES", "Insurance payment", "Balance due", "Adjustment"])
def test_summary_rows_are_skipped(text):
    assert parse_row(row(text, "$500.00")) is None


def test_uncoded_lines_are_kept_for_review_not_dropped():
    boxes = row("0250", "PHARMACY GENERAL", "$112.75", y=100) + row("85025", "CBC", "$84.00", y=200)
    p = parse_bill(boxes)
    assert [l["code"] for l in p["lines"]] == ["85025"]
    assert p["unreviewed_lines"][0]["description"] == "PHARMACY GENERAL"


def test_totals_check():
    boxes = row("85025", "CBC", "$84.00", y=100) + row("TOTAL CHARGES", "$84.00", y=200)
    assert parse_bill(boxes)["totals_match"] is True
    boxes = row("85025", "CBC", "$84.00", y=100) + row("TOTAL CHARGES", "$999.00", y=200)
    assert parse_bill(boxes)["totals_match"] is False


def test_rows_group_by_height_not_order():
    boxes = [Box("$84.00", 500, 102, 580, 130, 0.9), Box("85025", 0, 100, 80, 128, 0.9),
             Box("CBC", 100, 300, 180, 330, 0.9)]
    rows = group_rows(boxes)
    assert [[b.text for b in r] for r in rows] == [["85025", "$84.00"], ["CBC"]]


# ---- cross-checking ChatGPT ------------------------------------------------

def test_verify_flags_a_misread_charge():
    boxes = row("85025", "CBC", "$84.00")
    lines = [{"line_no": 1, "code": "85025", "charge": 84.0},
             {"line_no": 2, "code": "85025", "charge": 48.0}]  # vision misread
    out = verify_lines(lines, boxes)
    assert out[0]["verified"] is True
    assert out[1]["verified"] is False and out[1]["check"]["charge_seen"] is False


def test_verify_without_ocr_is_unknown():
    assert verify_lines([{"code": "1", "charge": 1.0}], None)[0]["verified"] is None


# ---- reader fallback order -------------------------------------------------

@pytest.fixture
def img(tmp_path, monkeypatch):
    p = tmp_path / "bill.png"
    p.write_bytes(b"fake")
    monkeypatch.setattr(reader, "UPLOADS", tmp_path)
    return "file:bill.png"


def test_demo_mode_unchanged(monkeypatch, tmp_path):
    demo = tmp_path / "maya.json"
    demo.write_text(json.dumps({"hospital_npi": "", "lines": []}))
    monkeypatch.setattr(reader, "DEMO_BILL", demo)
    assert reader.read_bill("", demo=True)["reader"] == "demo"


def test_ocr_first(img, monkeypatch):
    boxes = row("85025", "CBC", "$84.00", y=100) + row("TOTAL CHARGES", "$84.00", y=200)
    monkeypatch.setattr(engine, "run_ocr", lambda b: boxes)
    monkeypatch.setattr(reader, "_vision", lambda *a: pytest.fail("vision must not run"))
    out = reader.read_bill(img, demo=False)
    assert out["reader"] == "ocr" and out["lines"][0]["source"] == "ocr"


def test_falls_back_to_chatgpt_when_totals_do_not_add_up(img, monkeypatch):
    boxes = row("85025", "CBC", "$84.00", y=100) + row("TOTAL CHARGES", "$999.00", y=200)
    monkeypatch.setattr(engine, "run_ocr", lambda b: boxes)
    monkeypatch.setenv("VISION_API_KEY", "sk-test")
    monkeypatch.setattr(reader, "_vision", lambda *a: {"hospital_npi": "", "lines": [
        {"line_no": 1, "code": "85025", "description": "CBC", "units": 1, "charge": 84.0, "service_date": ""},
        {"line_no": 2, "code": "99999", "description": "?", "units": 1, "charge": 915.0, "service_date": ""}]})
    out = reader.read_bill(img, demo=False)
    assert out["reader"] == "vision"
    assert out["fallback_reason"] == "lines do not add up to the printed total"
    assert out["needs_review"] == [2]


def test_falls_back_to_chatgpt_when_ocr_missing(img, monkeypatch):
    monkeypatch.setattr(engine, "run_ocr", lambda b: None)
    monkeypatch.setenv("VISION_API_KEY", "sk-test")
    monkeypatch.setattr(reader, "_vision", lambda *a: {"hospital_npi": "", "lines": [
        {"line_no": 1, "code": "85025", "description": "CBC", "units": 1, "charge": 84.0, "service_date": ""}]})
    out = reader.read_bill(img, demo=False)
    assert out["reader"] == "vision" and out["lines"][0]["verified"] is None


def test_live_mode_never_substitutes_the_demo_bill(img, monkeypatch):
    monkeypatch.setattr(engine, "run_ocr", lambda b: None)
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    monkeypatch.setenv("BILLO_MODE", "live")
    with pytest.raises(ValueError, match="could not be read reliably"):
        reader.read_bill(img, demo=False)


# ---- real OCR on the synthetic bill image (skipped if RapidOCR missing) ----

@pytest.mark.skipif(not engine.available(), reason="rapidocr-onnxruntime not installed")
def test_real_ocr_on_synthetic_bill():
    p = parse_bill(engine.run_ocr(FIX.read_bytes()))
    got = [(l["code"], l["units"], l["charge"]) for l in p["lines"]]
    assert got == [("85025", 1, 84.0), ("85025", 1, 84.0), ("99284", 1, 2450.0), ("J1885", 2, 77.0)]
    assert p["unreviewed_lines"][0]["charge"] == 112.75
    assert p["hospital_npi"] == "1234567893" and p["totals_match"] is True
