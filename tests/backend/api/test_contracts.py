"""Public and authenticated Core API contract tests."""
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "api"))

os.environ["BILLO_MODE"] = "demo"
os.environ["DATABASE_URL"] = ""
os.environ["SENTRY_DSN"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402

client = TestClient(main.app)
headers = {"x-internal-token": main.TOKEN}


def test_health_is_public_and_reports_safe_runtime_modes():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["mode"] == "demo"
    assert payload["visa_qr"] == "simulate"
    assert "dsn" not in str(payload).lower()


def test_care_search_rejects_missing_internal_token():
    response = client.get("/care/search", params={"q": "knee pain", "near": "UCLA"})
    assert response.status_code == 401
    assert response.json()["detail"] == "bad internal token"


def test_care_search_maps_injury_words_to_knee_imaging_code():
    response = client.get("/care/search", params={"q": "ankle fall", "near": "UCLA"}, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "73560"
    assert len(payload["places"]) == 3
    assert all(place["price_typical"] >= place["price_low"] for place in payload["places"])
    assert all("picture_url" not in place for place in payload["places"])
    assert payload["location"] == "Los Angeles, CA"
    assert all("Chicago" not in place["address"] for place in payload["places"])


def test_care_search_honors_chicago_instead_of_reusing_los_angeles_results():
    response = client.get(
        "/care/search", params={"q": "broken leg", "near": "Chicago, IL"}, headers=headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["location"] == "Chicago, IL"
    assert len(payload["places"]) == 3
    assert all("Chicago" in place["address"] for place in payload["places"])
    assert all("Westwood" not in place["name"] for place in payload["places"])
    assert all("demo" in place["price_source"] for place in payload["places"])


def test_care_search_does_not_fall_back_to_la_for_an_unsupported_location():
    response = client.get(
        "/care/search", params={"q": "broken leg", "near": "Seattle, WA"}, headers=headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["location"] == "Seattle, WA"
    assert payload["places"] == []


def test_care_search_uses_office_visit_code_for_other_requests():
    response = client.get("/care/search", params={"q": "routine checkup"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["code"] == "99213"


def test_empty_upload_is_rejected_without_creating_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    response = client.post("/files", content=b"", headers=headers)
    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_upload_uses_allowlisted_extension_and_random_name(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    image = (ROOT / "tests/backend/ocr/fixtures/synthetic_bill.png").read_bytes()
    response = client.post("/files", content=image, headers={**headers, "content-type": "application/octet-stream"})
    assert response.status_code == 200
    file_name = response.json()["file_url"].removeprefix("file:")
    assert file_name.endswith(".png")
    assert "/" not in file_name and "\\" not in file_name
    assert (tmp_path / file_name).read_bytes() == image
    assert (tmp_path / file_name).stat().st_mode & 0o777 == 0o600


def test_after_care_rejects_unknown_payment_state():
    response = client.post(
        "/after-care/organize",
        json={"case_id": "bad-state", "lines": [], "payment_status": "maybe"},
        headers=headers,
    )
    assert response.status_code == 422
    assert "paid, unpaid, or unknown" in response.json()["detail"]


def test_missing_calendar_and_settlement_records_return_not_found():
    assert client.get("/ics/not-a-case").status_code == 404
    settlement = client.get("/visa/settlements/not-a-settlement", headers=headers)
    assert settlement.status_code == 404


def test_benefit_matching_uses_word_boundaries():
    response = client.post(
        "/benefits/check",
        json={"case_id": "word-boundary", "text": "I am researching classroom support."},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["paths"] == []


def test_schema_validation_rejects_non_numeric_estimate():
    response = client.post(
        "/estimates",
        json={"case_id": "invalid-estimate", "npi": "1999999901", "place": "Clinic", "amount": "many"},
        headers=headers,
    )
    assert response.status_code == 422


def test_upload_rejects_fake_image_bytes_and_invalid_length(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    assert client.post("/files", content=b"not an image", headers={**headers, "content-type": "image/png"}).status_code == 415
    assert client.post("/files", content=b"x", headers={**headers, "content-length": "invalid"}).status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_missing_document_is_not_implicitly_replaced_by_demo():
    result = client.post("/reader/extract", json={"case_id": "missing-upload"}, headers=headers)
    assert result.status_code == 422
    assert "Attach a bill" in result.json()["detail"]


def test_multi_unit_line_total_is_not_multiplied_twice():
    result = client.post("/after-care/organize", json={"case_id": "quantity-total", "lines": [
        {"line_no": 1, "code": "J1885", "description": "Medication", "units": 2, "charge": 77},
        {"line_no": 2, "code": "", "description": "Uncoded supply", "units": 1, "charge": 23},
    ]}, headers=headers)
    assert result.status_code == 200
    assert result.json()["total"] == 100
    assert result.json()["payment_status"] == "unknown"


def test_real_photo_upload_extract_organize_preserves_uncoded_lines(tmp_path, monkeypatch):
    from ocr import engine, reader
    if not engine.available():
        import pytest
        pytest.skip("RapidOCR is unavailable")
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    monkeypatch.setattr(reader, "UPLOADS", tmp_path)
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    image = (ROOT / "tests/backend/ocr/fixtures/synthetic_bill.png").read_bytes()
    uploaded = client.post("/files", content=image, headers={**headers, "content-type": "application/octet-stream"}).json()
    result = client.post("/reader/extract", json={"case_id": "real-image", **uploaded}, headers=headers)
    assert result.status_code == 200, result.text
    bill = result.json()
    assert bill["reader"] == "ocr"
    assert len(bill["lines"]) == 5
    assert len(bill["unreviewed_lines"]) == 1
    assert bill["needs_review"]
    assert list(tmp_path.iterdir()) == []
    organized = client.post("/after-care/organize", json={"case_id": "real-image", "lines": bill["lines"]}, headers=headers)
    assert organized.json()["total"] == 2807.75


def test_real_pdf_upload_is_rendered_before_ocr(tmp_path, monkeypatch):
    import pytest
    from PIL import Image
    from ocr import engine, reader
    pytest.importorskip("pypdfium2")
    if not engine.available():
        pytest.skip("RapidOCR is unavailable")
    monkeypatch.setattr(main, "UPLOADS", tmp_path)
    monkeypatch.setattr(reader, "UPLOADS", tmp_path)
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    output = io.BytesIO()
    with Image.open(ROOT / "tests/backend/ocr/fixtures/synthetic_bill.png") as image:
        image.convert("RGB").save(output, format="PDF")
    uploaded = client.post("/files", content=output.getvalue(), headers={**headers, "content-type": "application/pdf"}).json()
    result = client.post("/reader/extract", json={"case_id": "real-pdf", **uploaded}, headers=headers)
    assert result.status_code == 200, result.text
    bill = result.json()
    assert bill["page_count"] == 1
    assert bill["reader"] == "ocr"
    assert bill["parsed_total"] == 2807.75
    assert list(tmp_path.iterdir()) == []
