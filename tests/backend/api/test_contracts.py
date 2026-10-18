"""Public and authenticated Core API contract tests."""
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
    response = client.post("/files", content=b"not-real-image", headers={**headers, "content-type": "image/png"})
    assert response.status_code == 200
    file_name = response.json()["file_url"].removeprefix("file:")
    assert file_name.endswith(".png")
    assert "/" not in file_name and "\\" not in file_name
    assert (tmp_path / file_name).read_bytes() == b"not-real-image"


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
