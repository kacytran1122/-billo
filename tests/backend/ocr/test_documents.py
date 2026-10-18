"""Receipt, photo and PDF regression cases without any external model calls."""
import base64
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from ocr import documents, engine, reader
from ocr.engine import Box
from ocr.parse import find_total, parse_row


def png():
    output = io.BytesIO()
    Image.new("RGB", (100, 150), "white").save(output, format="PNG")
    return output.getvalue()


def pdf(count=1):
    output = io.BytesIO()
    images = [Image.new("RGB", (100, 150), "white") for _ in range(count)]
    images[0].save(output, format="PDF", save_all=True, append_images=images[1:])
    return output.getvalue()


def inline(data):
    return "data:application/octet-stream;base64," + base64.b64encode(data).decode()


def boxes(*rows):
    return [Box(text, i * 200, row * 100, i * 200 + 180, row * 100 + 25, 0.99)
            for row, texts in enumerate(rows) for i, text in enumerate(texts)]


def test_sniffs_file_bytes_instead_of_untrusted_mime():
    data = png()
    assert reader.load_image(inline(data)) == (data, "image/png")
    assert documents.content_type(pdf()) == "application/pdf"
    assert documents.content_type(b"RIFFxxxxWEBPxxxx") == "image/webp"


@pytest.mark.parametrize("value", ["http://127.0.0.1/private", "https://example.com/bill.png",
                                  "file:../.env", "file:..\\.env", "data:image/png;base64,??"])
def test_reader_refuses_remote_and_invalid_document_references(value):
    with pytest.raises(ValueError):
        reader.load_image(value)


def test_unsupported_or_corrupt_image_is_not_a_demo(monkeypatch):
    monkeypatch.setenv("BILLO_MODE", "demo")
    with pytest.raises(ValueError):
        reader.read_bill(inline(b"not a document"), demo=False)
    with pytest.raises(ValueError):
        reader.read_bill(inline(b"\x89PNG\r\n\x1a\ncorrupt"), demo=False)
    with pytest.raises(ValueError, match="Attach a bill"):
        reader.read_bill("", demo=False)


def test_decodes_short_pdf_pages():
    pytest.importorskip("pypdfium2")
    output = documents.pages(pdf(2), "application/pdf")
    assert len(output) == 2
    assert all(page.startswith(b"\x89PNG") for page in output)


def test_pdf_page_limit_is_explicit_not_silent_truncation():
    pytest.importorskip("pypdfium2")
    with pytest.raises(ValueError, match="split this document"):
        documents.pages(pdf(documents.MAX_PAGES + 1), "application/pdf")


def test_corrupt_pdf_fails_cleanly():
    pytest.importorskip("pypdfium2")
    with pytest.raises(ValueError, match="could not be opened"):
        documents.pages(b"%PDF-broken", "application/pdf")


def test_image_pixel_limit_precedes_rgb_decode(monkeypatch):
    monkeypatch.setattr(documents, "MAX_PIXELS", 100)
    with pytest.raises(ValueError, match="too large"):
        documents.pages(png(), "image/png")


def test_uncoded_receipt_lines_are_preserved_and_flagged(monkeypatch):
    monkeypatch.setattr(engine, "run_ocr", lambda _: boxes(
        ("CLINIC RECEIPT",), ("Office visit", "$120.00"), ("Lab service", "$30.00"),
        ("TOTAL", "$150.00"), ("Balance due", "$0.00")))
    monkeypatch.setattr(reader, "_vision", lambda *_: pytest.fail("Local receipt OCR should suffice"))
    output = reader.read_bill(inline(png()), demo=False)
    assert output["reader"] == "ocr"
    assert [line["code"] for line in output["lines"]] == ["", ""]
    assert output["parsed_total"] == 150
    assert output["needs_review"] == [1, 2]
    assert len(output["unreviewed_lines"]) == 2


def test_compact_phone_ocr_row_keeps_code_and_description():
    line = parse_row([Box("85025 CBC 1 $84.00", 0, 0, 500, 30, 0.95)])
    assert line["code"] == "85025"
    assert line["charge"] == 84
    assert "CBC" in line["description"]


@pytest.mark.parametrize("label", ["Receipt #12345", "Invoice:12345", "Reference 12345", "Account number 12345"])
def test_document_identifiers_are_not_invented_cpt_codes(label):
    line = parse_row([Box(label + " Clinic visit $84.00", 0, 0, 500, 30, 0.99)])
    assert line["code"] == ""


def test_ambiguous_payment_columns_are_not_auto_verified(monkeypatch):
    monkeypatch.setattr(engine, "run_ocr", lambda _: boxes(("Medical bill",), ("99213 Office visit $120.00 $20.00",)))
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ambiguous charge"):
        reader.read_bill(inline(png()), demo=False)


@pytest.mark.parametrize("text", ["Courtesy credit −$20.00", "Refund $20.00", "Adjustment -$20.00", "Supplies −$20.00"])
def test_credits_are_not_positive_service_charges(text):
    assert parse_row([Box(text, 0, 0, 500, 30, 0.99)]) is None


def test_vision_printed_total_retains_currency_formatting():
    result = reader._valid({"printed_total": "$1,200.00", "lines": [
        {"code": "85025", "description": "CBC", "charge": 84}]})
    assert result["printed_total"] == 1200


def test_paid_receipt_total_precedes_zero_balance():
    rows = [[Box(text, 0, i, 300, i + 1, 1)] for i, text in enumerate(
        ["TOTAL CHARGES $150.00", "Insurance payment $150.00", "Balance due $0.00"])]
    assert find_total(rows) == 150


def test_vision_validation_retains_uncoded_receipt_not_guessed_codes():
    result = reader._valid({"document_type": "receipt", "hospital_npi": "not-an-npi", "lines": [
        {"code": "guessed", "description": "Clinic visit", "charge": "$180.00", "units": 1}]})
    assert result["hospital_npi"] == ""
    assert result["lines"][0]["code"] == ""
    assert result["lines"][0]["charge"] == 180


@pytest.mark.parametrize("amount", ["NaN", "Infinity", -1, "unreadable"])
def test_vision_validation_rejects_invalid_amounts(amount):
    with pytest.raises(ValueError, match="no valid lines"):
        reader._valid({"lines": [{"code": "85025", "charge": amount}]})


def test_unverified_vision_lines_always_require_review(monkeypatch):
    monkeypatch.setattr(engine, "run_ocr", lambda _: None)
    monkeypatch.setenv("VISION_API_KEY", "test-not-a-secret")
    monkeypatch.setattr(reader, "_vision", lambda *_: {"lines": [
        {"line_no": 1, "code": "85025", "charge": 84, "description": "CBC", "units": 1}]})
    result = reader.read_bill(inline(png()), demo=False)
    assert result["needs_review"] == [1]
    assert result["lines"][0]["verified"] is None


def test_vision_failure_has_safe_response_and_no_demo_substitution(monkeypatch):
    monkeypatch.setenv("BILLO_MODE", "demo")
    monkeypatch.setenv("VISION_API_KEY", "test-not-a-secret")
    monkeypatch.setattr(engine, "run_ocr", lambda _: None)
    def fail(*_):
        raise RuntimeError("private patient and credential details")
    monkeypatch.setattr(reader, "_vision", fail)
    with pytest.raises(ValueError, match="could not finish") as exc:
        reader.read_bill(inline(png()), demo=False)
    assert "private patient" not in str(exc.value)


def test_vision_request_uses_normalized_pages_and_bounded_timeout(monkeypatch):
    import openai
    captured = {}
    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=self)
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"lines":[{"code":"85025","charge":84,"description":"CBC"}]}'))])
    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    reader._vision([png(), png()], "image/png", strict=False)
    assert captured["timeout"] == 35 and captured["max_retries"] == 0
    images = captured["messages"][1]["content"][1:]
    assert len(images) == 2
    assert all(item["image_url"]["url"].startswith("data:image/png;base64,") for item in images)
