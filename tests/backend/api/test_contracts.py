"""Public and authenticated Core API contract tests."""
import io
import os
import re
import sys
import threading
import time
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


def start_operation(case_id: str, kind: str, request_id: str) -> str:
    response = client.post("/operations/start", json={
        "case_id": case_id, "kind": kind, "request_id": request_id,
    }, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    return request_id


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
    assert all(
        place["price_high"] >= place["price_typical"] >= place["price_low"]
        for place in payload["places"]
    )
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


def test_care_search_uses_regional_percentiles_instead_of_static_place_prices(monkeypatch):
    non_er = [
        {"code": "73560", "region": "chicago", "kind": "clinic", "price": value}
        for value in range(100, 200, 10)
    ]
    er = [
        {"code": "73560", "region": "chicago", "kind": "er", "price": value}
        for value in range(900, 1000, 10)
    ]
    monkeypatch.setattr(main.store, "_csv_rows", non_er + er)

    payload = client.get(
        "/care/search", params={"q": "knee", "near": "Chicago, IL"}, headers=headers
    ).json()
    clinic = next(place for place in payload["places"] if place["kind"] == "clinic")
    emergency = next(place for place in payload["places"] if place["kind"] == "er")
    assert (clinic["price_low"], clinic["price_typical"], clinic["price_high"]) == (
        101.0, 145.0, 189.0,
    )
    assert (emergency["price_low"], emergency["price_typical"], emergency["price_high"]) == (
        901.0, 945.0, 989.0,
    )
    assert "regional price cohort" in clinic["price_source"].lower()
    assert "p10/p50/p90" in clinic["price_source"]
    assert "curated" not in clinic["price_source"].lower()


def test_care_search_curated_fallback_is_explicit_when_regional_cohort_is_missing(monkeypatch):
    monkeypatch.setattr(main.store, "_csv_rows", [])
    payload = client.get(
        "/care/search", params={"q": "knee", "near": "Chicago, IL"}, headers=headers
    ).json()
    assert all("curated synthetic demo" in place["price_source"].lower() for place in payload["places"])
    assert all("no regional 73560" in place["price_source"].lower() for place in payload["places"])


def test_selected_location_overrides_an_old_city_in_the_query_both_directions():
    moved_to_la = client.get(
        "/care/search",
        params={"q": "knee X-ray in Chicago", "near": "Los Angeles, CA"},
        headers=headers,
    ).json()
    assert moved_to_la["location"] == "Los Angeles, CA"
    assert all("Chicago" not in place["address"] for place in moved_to_la["places"])

    moved_to_chicago = client.get(
        "/care/search",
        params={"q": "knee X-ray in Los Angeles", "near": "Chicago, IL"},
        headers=headers,
    ).json()
    assert moved_to_chicago["location"] == "Chicago, IL"
    assert all("Chicago" in place["address"] for place in moved_to_chicago["places"])


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
    request_id = start_operation("bad-state", "after_care", "bad-state-request")
    response = client.post(
        "/after-care/organize",
        json={
            "case_id": "bad-state", "request_id": request_id,
            "lines": [], "payment_status": "maybe",
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert "paid, unpaid, or unknown" in response.json()["detail"]


def test_operations_are_private_conditionally_canceled_and_never_echo_request_ids():
    case_id = "operation-contract"
    request_id = "operation-contract-current"
    unauthorized = client.post("/operations/start", json={
        "case_id": case_id, "kind": "after_care", "request_id": request_id,
    })
    assert unauthorized.status_code == 401

    start_operation(case_id, "after_care", request_id)
    assert main.store.operation_active(case_id, "after_care", request_id) is True
    wrong = client.post("/operations/cancel", json={
        "case_id": case_id, "kind": "after_care", "request_id": "wrong-request",
    }, headers=headers)
    assert wrong.json() == {"canceled": False}
    assert request_id not in wrong.text
    assert main.store.operation_active(case_id, "after_care", request_id) is True
    canceled = client.post("/operations/cancel", json={
        "case_id": case_id, "kind": "after_care", "request_id": request_id,
    }, headers=headers)
    assert canceled.json() == {"canceled": True}
    assert request_id not in canceled.text
    assert main.store.operation_active(case_id, "after_care", request_id) is False


def test_stale_and_expired_after_care_operations_cannot_mutate_records():
    stale_case = "stale-operation-case"
    start_operation(stale_case, "after_care", "current-request")
    stale = client.post("/after-care/organize", json={
        "case_id": stale_case, "request_id": "superseded-request",
        "lines": [{"line_no": 1, "description": "stale", "charge": 999}],
    }, headers=headers)
    assert stale.status_code == 409
    assert main.store.get_after_care(stale_case) is None

    expired_case = "expired-operation-case"
    request_id = start_operation(expired_case, "after_care", "expired-request")
    main.store._mem["operations"][expired_case]["updated_at"] = (
        time.time() - main.store.OPERATION_TTL_SECONDS - 1
    )
    expired = client.post("/after-care/organize", json={
        "case_id": expired_case, "request_id": request_id,
        "lines": [{"line_no": 1, "description": "expired", "charge": 500}],
    }, headers=headers)
    assert expired.status_code == 409
    assert main.store.get_after_care(expired_case) is None


def test_run_operation_serializes_a_new_start_behind_the_current_mutation():
    case_id = "operation-ordering-case"
    first = "first-request"
    second = "second-request"
    start_operation(case_id, "after_care", first)
    begin_replacement = threading.Event()
    replacement_done = threading.Event()

    def replace_operation():
        begin_replacement.wait()
        main.store.start_operation(case_id, "after_care", second)
        replacement_done.set()

    thread = threading.Thread(target=replace_operation)
    thread.start()

    def mutate():
        begin_replacement.set()
        assert replacement_done.wait(0.05) is False
        main.store.save_after_care(case_id, {
            "case_id": case_id, "hospital_npi": "", "total": 100,
            "payment_status": "unknown", "provider_match": False,
            "visit_items_matched": 0,
        })
        return {"total": 100}

    result = main.store.run_operation(
        case_id, "after_care", first, "after_care", mutate,
    )
    assert result == {"total": 100}
    thread.join(timeout=1)
    assert replacement_done.is_set()
    assert main.store.operation_active(case_id, "after_care", first) is False
    assert main.store.operation_active(case_id, "after_care", second) is True


def test_successful_after_care_is_replayable_without_rerunning_the_write(monkeypatch):
    case_id = "successful-operation-case"
    request_id = start_operation(case_id, "after_care", "successful-request")
    original_save = main.store.save_after_care
    calls = []

    def counted_save(saved_case_id, record):
        calls.append((saved_case_id, record["total"]))
        return original_save(saved_case_id, record)

    monkeypatch.setattr(main.store, "save_after_care", counted_save)
    payload = {
        "case_id": case_id, "request_id": request_id,
        "lines": [{"line_no": 1, "description": "Visit", "charge": 125}],
    }
    response = client.post("/after-care/organize", json=payload, headers=headers)
    # A delayed/retried start for the same logical request must not erase the
    # completed result and reactivate its mutation grant.
    start_operation(case_id, "after_care", request_id)
    replay = client.post("/after-care/organize", json={
        **payload,
        "lines": [{"line_no": 1, "description": "Must not replace", "charge": 999}],
    }, headers=headers)
    assert response.status_code == 200 and replay.status_code == 200
    assert replay.json() == response.json()
    assert calls == [(case_id, 125)]
    assert main.store.operation_active(case_id, "after_care", request_id) is False
    cached = main.store._mem["operations"][case_id]["result"]
    assert "lines" not in cached
    assert "description" not in str(cached).lower()
    assert "Visit" not in str(cached)


def test_start_is_case_wide_and_cross_kind_supersedes_the_previous_operation():
    case_id = "cross-kind-operation-case"
    after_request = start_operation(case_id, "after_care", "after-request")
    settlement_request = start_operation(case_id, "settlement", "settlement-request")
    assert main.store.operation_active(case_id, "after_care", after_request) is False
    assert main.store.operation_active(case_id, "settlement", settlement_request) is True
    canceled = client.post("/operations/cancel", json={
        "case_id": case_id, "kind": "after_care", "request_id": after_request,
    }, headers=headers)
    assert canceled.json() == {"canceled": False}
    assert main.store.operation_active(case_id, "settlement", settlement_request) is True


def test_operation_status_is_authenticated_scrubbed_and_completed_until_next_start():
    case_id = "operation-status-private-case"
    request_id = start_operation(case_id, "after_care", "private-request-id")
    main.store.run_operation(
        case_id, "after_care", request_id, "after_care",
        lambda: {
            "case_id": case_id, "request_id": request_id, "total": 42,
            "nested": {"case_id": case_id, "safe": True},
        },
    )
    body = {"case_id": case_id, "kind": "after_care", "request_id": request_id}
    assert client.post("/operations/status", json=body).status_code == 401
    completed = client.post("/operations/status", json=body, headers=headers)
    assert completed.status_code == 200
    assert completed.json() == {
        "status": "completed", "action": "after_care",
        "result": {"total": 42},
    }
    assert case_id not in completed.text and request_id not in completed.text

    next_request = start_operation(case_id, "settlement", "next-request")
    assert client.post("/operations/status", json=body, headers=headers).json() == {
        "status": "inactive",
    }
    active = client.post("/operations/status", json={
        "case_id": case_id, "kind": "settlement", "request_id": next_request,
    }, headers=headers)
    assert active.json() == {"status": "active"}


def test_completed_operation_remains_truthful_without_reauthorizing_its_mutation():
    case_id = "aged-completed-operation"
    request_id = start_operation(case_id, "after_care", "aged-completed-request")
    payload = {
        "case_id": case_id, "request_id": request_id,
        "lines": [{"line_no": 1, "description": "Original private line", "charge": 55}],
    }
    original = client.post("/after-care/organize", json=payload, headers=headers)
    assert original.status_code == 200
    main.store._mem["operations"][case_id]["updated_at"] = time.time() - 24 * 60 * 60
    body = {"case_id": case_id, "kind": "after_care", "request_id": request_id}
    completed = client.post("/operations/status", json=body, headers=headers).json()
    assert completed["status"] == "completed"
    assert completed["action"] == "after_care"
    assert completed["result"]["total"] == 55
    assert "lines" not in completed["result"]
    assert "private" not in str(completed).lower()

    # Retrying the same start cannot turn a completed request back into an
    # active authorization or replace its already-committed domain record.
    start_operation(case_id, "after_care", request_id)
    replay = client.post("/after-care/organize", json={
        "case_id": case_id, "request_id": request_id,
        "lines": [{"line_no": 1, "description": "must not write", "charge": 999}],
    }, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == original.json()
    assert main.store.get_after_care(case_id)["total"] == 55


def test_every_settlement_mutation_rejects_an_inactive_request_before_domain_checks():
    requests = [
        ("/visa/qr/inspect", {"case_id": "inactive-inspect", "request_id": "inactive"}),
        ("/visa/qr/approve", {
            "case_id": "inactive-approve", "request_id": "inactive",
            "review_id": "missing", "explicit_approval": True,
        }),
        ("/visa/reimbursement/payout", {
            "case_id": "inactive-reimburse", "request_id": "inactive",
            "benefit_name": "HSA", "amount": 10,
            "benefit_approved": True, "explicit_patient_approval": True,
        }),
    ]
    for path, payload in requests:
        response = client.post(path, json=payload, headers=headers)
        assert response.status_code == 409
        assert "stale, expired, or inactive" in response.json()["detail"]


def test_successful_reimbursement_consumes_the_settlement_operation():
    case_id = "reimbursement-operation-case"
    main.store.save_after_care(case_id, {
        "case_id": case_id, "hospital_npi": "", "total": 200,
        "payment_status": "paid", "provider_match": False,
        "visit_items_matched": 0,
    })
    benefit_name = "HSA self-reimbursement"
    main.store.save_benefit_check(case_id, {
        "paths": [{"name": benefit_name, "needed": "receipt"}],
    })
    request_id = start_operation(case_id, "settlement", "reimbursement-request")
    response = client.post("/visa/reimbursement/payout", json={
        "case_id": case_id, "request_id": request_id,
        "benefit_name": benefit_name, "amount": 100,
        "benefit_approved": True, "explicit_patient_approval": True,
    }, headers=headers)
    assert response.status_code == 200
    assert main.store.operation_active(case_id, "settlement", request_id) is False


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


def test_opaque_case_link_drives_saved_during_and_after_snapshots():
    case_id = "private-case-contract"
    saved = client.post("/estimates", json={
        "case_id": case_id,
        "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)",
        "code": "73560",
        "amount": 240,
        "calendar_start": 1893456000,
        "calendar_end": 1893459600,
    }, headers=headers)
    assert saved.status_code == 200
    links = saved.json()
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", links["token"])
    assert case_id not in str(links)
    assert links["visit_url"].endswith("/visit/" + links["token"])
    assert links["ics_url"].endswith(f"/public/cases/{links['token']}/calendar.ics")
    repeated = client.post("/case-links", json={"case_id": case_id}, headers=headers).json()
    assert repeated["token"] == links["token"]

    token_hash = main.public_links.token_hash(links["token"])
    assert links["token"] not in main.store._mem["public_links"]
    assert token_hash in main.store._mem["public_links"]

    public = client.get(f"/public/cases/{links['token']}")
    assert public.status_code == 200
    assert public.headers["cache-control"].startswith("private, no-store")
    assert public.headers["referrer-policy"] == "no-referrer"
    snapshot = public.json()
    assert snapshot["stage"] == "saved"
    assert snapshot["data_mode"] == "demo"
    assert snapshot["provider"]["address"].startswith("10900 Wilshire")
    assert snapshot["estimate"]["amount"] == 240
    assert case_id not in str(snapshot)
    assert main.TOKEN not in str(snapshot)
    assert "provider_npi" not in str(snapshot)
    assert "handle_hash" not in str(snapshot)

    visit = client.post("/visit-events", json={
        "case_id": case_id, "text": "The paperwork lists 73560",
    }, headers=headers)
    assert visit.status_code == 200
    during = client.get(f"/public/cases/{links['token']}").json()
    assert during["stage"] == "during"
    assert during["visit"]["items"][0]["label"] == "Knee X-ray"
    assert during["visit"]["running_total"] > 240

    request_id = start_operation(case_id, "after_care", "private-case-organize")
    organized = client.post("/after-care/organize", json={
        "case_id": case_id,
        "request_id": request_id,
        "hospital_npi": "1999999901",
        "payment_status": "unpaid",
        "reader": "ocr",
        "document_type": "bill",
        "lines": [{
            "line_no": 1, "code": "73560", "description": "Knee X-ray",
            "units": 1, "charge": 360, "service_date": "2026-10-18",
        }],
    }, headers=headers)
    assert organized.status_code == 200
    after = client.get(f"/public/cases/{links['token']}").json()
    assert after["stage"] == "after"
    assert after["data_mode"] == "mixed"
    assert after["document"]["reader"] == "ocr"
    assert after["document"]["lines"][0]["amount"] == 360
    assert case_id not in str(after)

    calendar = client.get(f"/public/cases/{links['token']}/calendar.ics")
    assert calendar.status_code == 200
    assert case_id not in calendar.text
    assert "LOCATION:10900 Wilshire" in calendar.text


def test_saved_care_option_without_conversation_time_omits_calendar_actions():
    case_id = "saved-option-without-time"
    links = client.post("/estimates", json={
        "case_id": case_id,
        "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)",
        "amount": 240,
    }, headers=headers).json()
    assert "ics_url" not in links and "gcal_url" not in links
    snapshot = client.get(f"/public/cases/{links['token']}").json()
    assert snapshot["provider"]["address"].startswith("10900 Wilshire")
    assert snapshot["provider"]["directions_url"].startswith("https://www.google.com/maps/search/")
    assert snapshot["estimate"]["amount"] == 240
    assert snapshot["calendar"] is None
    assert client.get(f"/public/cases/{links['token']}/calendar.ics").status_code == 404


def test_calendar_requires_a_complete_valid_user_supplied_range():
    base = {
        "case_id": "invalid-calendar-range", "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)", "amount": 240,
    }
    missing_end = client.post(
        "/estimates", json={**base, "calendar_start": 1893456000}, headers=headers,
    )
    assert missing_end.status_code == 422
    backwards = client.post(
        "/estimates",
        json={**base, "calendar_start": 1893459600, "calendar_end": 1893456000},
        headers=headers,
    )
    assert backwards.status_code == 422


def test_document_first_case_gets_opaque_after_only_snapshot_without_invented_care_plan():
    case_id = "document-first-private-case"
    npi = "1888888888"
    request_id = start_operation(case_id, "after_care", "document-first-organize")
    organized = client.post("/after-care/organize", json={
        "case_id": case_id,
        "request_id": request_id,
        "hospital_npi": npi,
        "payment_status": "unknown",
        "reader": "ocr",
        "document_type": "bill",
        "lines": [{
            "line_no": 1,
            "code": "99213",
            "description": "Office visit",
            "units": 1,
            "charge": 185,
            "service_date": "2026-10-18",
        }],
    }, headers=headers)
    assert organized.status_code == 200
    assert organized.json()["provider_match"] is False

    created = client.post("/case-links", json={"case_id": case_id}, headers=headers)
    assert created.status_code == 200
    links = created.json()
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", links["token"])
    assert links["visit_url"].endswith("/visit/" + links["token"])
    assert "ics_url" not in links and "gcal_url" not in links
    assert case_id not in str(links)

    public = client.get(f"/public/cases/{links['token']}")
    assert public.status_code == 200
    snapshot = public.json()
    assert snapshot["stage"] == "after"
    assert snapshot["data_mode"] == "patient_provided"
    assert snapshot["provider"] is None
    assert snapshot["estimate"] is None
    assert snapshot["calendar"] is None
    assert snapshot["visit"] == {"items": [], "running_total": 0.0, "currency": "USD"}
    assert snapshot["document"]["total"] == 185
    assert snapshot["document"]["lines"][0]["label"] == "Office visit"
    assert snapshot["document"]["provider_match"] is False
    assert case_id not in str(snapshot)
    assert npi not in str(snapshot)
    assert "case_id" not in str(snapshot)
    assert "provider_npi" not in str(snapshot)

    calendar = client.get(f"/public/cases/{links['token']}/calendar.ics")
    assert calendar.status_code == 404


def test_demo_estimate_and_demo_document_keep_demo_provenance():
    case_id = "all-demo-case-contract"
    links = client.post("/estimates", json={
        "case_id": case_id,
        "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)",
        "amount": 240,
        "data_mode": "demo",
    }, headers=headers).json()
    request_id = start_operation(case_id, "after_care", "demo-document-organize")
    organized = client.post("/after-care/organize", json={
        "case_id": case_id,
        "request_id": request_id,
        "payment_status": "unpaid",
        "reader": "demo",
        "document_type": "bill",
        "lines": [{"line_no": 1, "code": "99213", "description": "Visit", "charge": 300}],
    }, headers=headers)
    assert organized.status_code == 200
    snapshot = client.get(f"/public/cases/{links['token']}").json()
    assert snapshot["data_mode"] == "demo"


def test_document_review_metadata_is_persisted_as_line_numbers_and_exposed_per_line():
    case_id = "document-review-contract"
    fallback_reason = "lines do not add up to the printed total"
    request_id = start_operation(case_id, "after_care", "document-review-organize")
    organized = client.post("/after-care/organize", json={
        "case_id": case_id,
        "request_id": request_id,
        "payment_status": "unknown",
        "reader": "vision",
        "document_type": "unknown",
        "needs_review": [2, 2, 99],
        "unreviewed_lines": [1, 99],
        "fallback_reason": fallback_reason,
        "lines": [
            {"line_no": 1, "code": "", "description": "Supply", "charge": 25},
            {"line_no": 2, "code": "85025", "description": "Lab", "charge": 75},
            {"line_no": 3, "code": "99213", "description": "Visit", "charge": 100},
        ],
    }, headers=headers)
    assert organized.status_code == 200
    assert organized.json()["needs_review"] == [2]
    assert organized.json()["unreviewed_lines"] == [1]
    assert organized.json()["fallback_reason"] == fallback_reason

    stored = main.store.get_after_care(case_id)
    assert stored["needs_review"] == [2]
    assert stored["unreviewed_lines"] == [1]
    assert all(isinstance(number, int) for number in stored["unreviewed_lines"])
    assert stored["fallback_reason"] == fallback_reason

    token = client.post("/case-links", json={"case_id": case_id}, headers=headers).json()["token"]
    document = client.get(f"/public/cases/{token}").json()["document"]
    assert document["review_status"] == "review_needed"
    assert document["needs_review"] == [2]
    assert document["unreviewed_lines"] == [1]
    assert document["fallback_reason"] == fallback_reason
    assert document["summary"] == "Bill or receipt organized from 3 charge line(s)."
    assert document["lines"][0]["needs_review"] is True
    assert document["lines"][0]["review_reasons"] == ["No readable billing code"]
    assert document["lines"][1]["needs_review"] is True
    assert document["lines"][1]["review_reasons"] == ["Extracted value needs confirmation"]
    assert document["lines"][2]["needs_review"] is False
    assert document["lines"][2]["review_reasons"] == []
    assert "flagged lines" in document["next_steps"][0]


def test_document_without_reader_flags_has_organized_review_status():
    case_id = "document-organized-contract"
    request_id = start_operation(case_id, "after_care", "document-organized-request")
    response = client.post("/after-care/organize", json={
        "case_id": case_id,
        "request_id": request_id,
        "payment_status": "paid",
        "reader": "ocr",
        "document_type": "receipt",
        "lines": [{"line_no": 1, "code": "99213", "description": "Visit", "charge": 100}],
    }, headers=headers)
    assert response.status_code == 200
    token = client.post("/case-links", json={"case_id": case_id}, headers=headers).json()["token"]
    document = client.get(f"/public/cases/{token}").json()["document"]
    assert document["review_status"] == "organized"
    assert document["needs_review"] == []
    assert document["unreviewed_lines"] == []
    assert document["fallback_reason"] == ""
    assert document["lines"][0]["needs_review"] is False
    assert "organized record" in document["next_steps"][0]


def test_chicago_visit_service_is_recorded_unpriced_without_los_angeles_fallback(monkeypatch):
    monkeypatch.setattr(main.store, "_csv_rows", [
        {"code": "73560", "region": "los-angeles", "kind": "urgent_care", "price": 100 + i}
        for i in range(10)
    ])
    case_id = "chicago-location-specific-case"
    links = client.post("/estimates", json={
        "case_id": case_id, "npi": "1999999911",
        "place": "Chicago Urgent Care (demo)", "amount": 260,
    }, headers=headers).json()
    saved = main.store.get_estimate(case_id)
    assert saved["region"] == "chicago"
    assert saved["kind"] == "urgent_care"

    logged = client.post("/visit-events", json={
        "case_id": case_id, "text": "The paperwork lists 73560",
    }, headers=headers)
    assert logged.status_code == 200
    assert "no location-appropriate price data" in logged.json()["say"].lower()
    assert logged.json()["total"] == 260

    snapshot = client.get(f"/public/cases/{links['token']}").json()
    assert snapshot["stage"] == "during"
    assert snapshot["visit"]["running_total"] == 260
    assert snapshot["visit"]["items"][0]["amount"] is None
    assert snapshot["visit"]["items"][0]["qualifier"] == "unpriced"
    assert "location-appropriate" in snapshot["visit"]["items"][0]["source_label"]


def test_er_visit_pricing_uses_only_er_rows_not_outpatient_rows(monkeypatch):
    outpatient = [
        {"code": "73560", "region": "los-angeles", "kind": "urgent_care", "price": 100 + i}
        for i in range(10)
    ]
    emergency = [
        {"code": "73560", "region": "los-angeles", "kind": "er", "price": 900 + i}
        for i in range(10)
    ]
    monkeypatch.setattr(main.store, "_csv_rows", outpatient + emergency)
    case_id = "er-kind-specific-case"
    links = client.post("/estimates", json={
        "case_id": case_id, "npi": "1999999903",
        "place": "Santa Monica Emergency Room (demo)", "amount": 1800,
    }, headers=headers).json()
    saved = main.store.get_estimate(case_id)
    assert saved["region"] == "los-angeles"
    assert saved["kind"] == "er"

    logged = client.post("/visit-events", json={
        "case_id": case_id, "text": "The paperwork lists 73560",
    }, headers=headers)
    assert logged.status_code == 200
    snapshot = client.get(f"/public/cases/{links['token']}").json()
    item = snapshot["visit"]["items"][0]
    assert item["amount"] == 904.5
    assert item["amount"] > max(row["price"] for row in outpatient)
    assert item["qualifier"] == "estimated"


def test_ambiguous_visit_phrase_is_one_unpriced_item_and_literal_code_is_one_priced_item():
    ambiguous_case = "ambiguous-xray-service"
    ambiguous_links = client.post("/estimates", json={
        "case_id": ambiguous_case,
        "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)",
        "amount": 240,
    }, headers=headers).json()
    ambiguous = client.post("/visit-events", json={
        "case_id": ambiguous_case,
        "text": "They did an X-ray",
    }, headers=headers)
    assert ambiguous.status_code == 200
    assert ambiguous.json()["total"] == 240
    assert ambiguous.json()["ambiguous_services"] == [{
        "service": "X-ray", "candidate_codes": ["73560", "73562"],
    }]
    assert "exact billing code" in ambiguous.json()["say"].lower()
    stored_ambiguous = main.store.get_visit_events(ambiguous_case)
    assert len(stored_ambiguous) == 1
    assert stored_ambiguous[0]["code"] == "73560|73562"
    assert stored_ambiguous[0]["est_price"] is None
    assert main.store.visit_codes(ambiguous_case) == {"73560", "73562"}

    public = client.get(f"/public/cases/{ambiguous_links['token']}").json()
    assert public["visit"]["running_total"] == 240
    assert public["visit"]["items"] == [{
        "label": "X-ray",
        "code": "",
        "amount": None,
        "currency": "USD",
        "qualifier": "Exact code needed: 73560 or 73562",
        "source_label": "No amount added until the exact billing code is known",
    }]

    exact_case = "literal-xray-code"
    client.post("/estimates", json={
        "case_id": exact_case,
        "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)",
        "amount": 240,
    }, headers=headers)
    exact = client.post("/visit-events", json={
        "case_id": exact_case,
        "text": "The billing code is 73560",
    }, headers=headers)
    assert exact.status_code == 200
    assert exact.json()["total"] > 240
    stored_exact = main.store.get_visit_events(exact_case)
    assert len(stored_exact) == 1
    assert stored_exact[0]["code"] == "73560"
    assert stored_exact[0]["est_price"] is not None
    assert "73562" not in main.store.visit_codes(exact_case)


def test_wallet_handoff_uses_scoped_short_lived_bearer_token():
    case_id = "wallet-public-contract"
    links = client.post("/estimates", json={
        "case_id": case_id, "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)", "amount": 310,
    }, headers=headers).json()
    after_request = start_operation(case_id, "after_care", "wallet-after-care")
    client.post("/after-care/organize", json={
        "case_id": case_id, "request_id": after_request,
        "hospital_npi": "1999999901", "payment_status": "unpaid",
        "lines": [{"line_no": 1, "code": "99213", "description": "Office visit", "charge": 310}],
    }, headers=headers)
    inspect_request = start_operation(case_id, "settlement", "wallet-inspect")
    review = client.post("/visa/qr/inspect", json={
        "case_id": case_id, "request_id": inspect_request,
        "demo": True, "expected_invoice": "INV-310",
    }, headers=headers).json()
    assert main.store.operation_active(case_id, "settlement", inspect_request) is False
    inspect_cached = main.store._mem["operations"][case_id]["result"]
    assert "invoice" not in inspect_cached and "case_id" not in inspect_cached
    approve_request = start_operation(case_id, "settlement", "wallet-approve")
    approve_payload = {
        "case_id": case_id, "request_id": approve_request,
        "review_id": review["settlement_id"], "explicit_approval": True,
    }
    approved = client.post("/visa/qr/approve", json=approve_payload, headers=headers)
    assert approved.status_code == 200
    assert main.store.operation_active(case_id, "settlement", approve_request) is False
    approval = approved.json()
    wallet_token = approval["handoff_url"].rsplit("/", 1)[-1]
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", wallet_token)
    assert case_id not in approval["handoff_url"]
    assert case_id not in approval["wallet_api_url"]
    durable = main.store.get_settlement(review["settlement_id"])
    assert "handoff_url" not in durable and "wallet_api_url" not in durable
    operation_cache = main.store._mem["operations"][case_id]["result"]
    serialized_cache = str(operation_cache).lower()
    assert "handoff_url" not in operation_cache
    assert "wallet_api_url" not in operation_cache
    assert "/wallet/" not in serialized_cache
    assert wallet_token not in serialized_cache

    replay = client.post("/visa/qr/approve", json=approve_payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == approval
    status = client.post("/operations/status", json={
        "case_id": case_id, "kind": "settlement", "request_id": approve_request,
    }, headers=headers)
    assert status.json() == {
        "status": "completed", "action": "approve_qr", "result": approval,
    }
    assert wallet_token not in str(main.store._mem["operations"][case_id])

    # Completion truth outlives the short bearer lifetime. Status re-derives
    # and renews the deterministic URL without ever persisting its plaintext.
    main.store._mem["operations"][case_id]["updated_at"] = time.time() - 24 * 60 * 60
    token_hash = main.public_links.token_hash(wallet_token)
    main.store._mem["public_links"][token_hash]["expires_at"] = time.time() - 1
    renewed = client.post("/operations/status", json={
        "case_id": case_id, "kind": "settlement", "request_id": approve_request,
    }, headers=headers)
    assert renewed.status_code == 200
    assert renewed.json()["status"] == "completed"
    assert renewed.json()["action"] == "approve_qr"
    assert renewed.json()["result"]["handoff_url"] == approval["handoff_url"]
    assert main.store._mem["public_links"][token_hash]["expires_at"] > time.time()
    assert wallet_token not in str(main.store._mem["operations"][case_id])

    wallet = client.get(f"/public/wallet/{wallet_token}")
    assert wallet.status_code == 200
    assert wallet.headers["referrer-policy"] == "no-referrer"
    payload = wallet.json()
    assert payload["merchant_name"] == "WESTWOOD URGENT CARE DEMO"
    assert payload["amount"] == 310
    assert payload["currency"] == "USD"
    assert all(check["passed"] for check in payload["checks"])
    assert case_id not in str(payload)
    assert client.get(f"/public/cases/{links['token']}").json()["wallet_url"].endswith(wallet_token)


def test_default_demo_wallet_invoice_is_keyed_and_never_exposes_case_id():
    case_id = "wallet-default-invoice-private-case"
    client.post("/estimates", json={
        "case_id": case_id, "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)", "amount": 225,
    }, headers=headers)
    after_request = start_operation(case_id, "after_care", "invoice-after-care")
    client.post("/after-care/organize", json={
        "case_id": case_id, "request_id": after_request,
        "hospital_npi": "1999999901", "payment_status": "unpaid",
        "lines": [{"line_no": 1, "code": "99213", "description": "Office visit", "charge": 225}],
    }, headers=headers)
    inspect_request = start_operation(case_id, "settlement", "invoice-inspect")
    review = client.post("/visa/qr/inspect", json={
        "case_id": case_id, "request_id": inspect_request, "demo": True,
    }, headers=headers).json()
    assert review["invoice_checked"] is True
    assert review["invoice"].startswith("BILLO-")
    assert case_id not in review["invoice"]
    approve_request = start_operation(case_id, "settlement", "invoice-approve")
    approved = client.post("/visa/qr/approve", json={
        "case_id": case_id, "request_id": approve_request,
        "review_id": review["settlement_id"], "explicit_approval": True,
    }, headers=headers).json()
    assert case_id not in approved["handoff_url"]
    wallet_token = approved["handoff_url"].rsplit("/", 1)[-1]
    public = client.get(f"/public/wallet/{wallet_token}").json()
    assert case_id not in str(public)
    assert public["invoice"] == review["invoice"]
    assert any(check["id"] == "invoice" and check["passed"] for check in public["checks"])


def test_wallet_does_not_claim_invoice_match_when_no_invoice_was_expected():
    case_id = "wallet-no-invoice-comparison-case"
    client.post("/estimates", json={
        "case_id": case_id, "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)", "amount": 200,
    }, headers=headers)
    after_request = start_operation(case_id, "after_care", "no-invoice-after-care")
    client.post("/after-care/organize", json={
        "case_id": case_id, "request_id": after_request,
        "hospital_npi": "1999999901", "payment_status": "unpaid",
        "lines": [{"line_no": 1, "code": "99213", "description": "Office visit", "charge": 200}],
    }, headers=headers)
    qr_payload = main.visa.demo_qr("Westwood Urgent Care (demo)", 200, "UNCOMPARED")
    inspect_request = start_operation(case_id, "settlement", "no-invoice-inspect")
    review = client.post("/visa/qr/inspect", json={
        "case_id": case_id, "request_id": inspect_request, "qr_payload": qr_payload,
    }, headers=headers).json()
    assert review["trusted"] is True
    assert review["invoice_checked"] is False
    approve_request = start_operation(case_id, "settlement", "no-invoice-approve")
    approved = client.post("/visa/qr/approve", json={
        "case_id": case_id, "request_id": approve_request,
        "review_id": review["settlement_id"], "explicit_approval": True,
    }, headers=headers).json()
    token = approved["handoff_url"].rsplit("/", 1)[-1]
    public = client.get(f"/public/wallet/{token}").json()
    assert all(check["id"] != "invoice" for check in public["checks"])


def test_dispute_letter_fails_closed_without_case_specific_evidence():
    case_id = "scope-separated-private-case"
    case_links = client.post("/estimates", json={
        "case_id": case_id, "npi": "1999999901",
        "place": "Westwood Urgent Care (demo)", "amount": 240,
    }, headers=headers).json()
    response = client.post("/disputes/letter", json={"case_id": case_id}, headers=headers)
    assert response.status_code == 409
    assert "evidence-backed" in response.json()["detail"]
    assert client.get(f"/public/cases/{case_links['token']}").status_code == 200
    assert client.get(f"/letters/{case_links['token']}.txt").status_code == 404


def test_whatsapp_link_code_is_strong_one_time_and_public_status_is_non_identifying(monkeypatch):
    monkeypatch.setenv("PHOTON_WHATSAPP_ADDRESS", "+14155550123")
    monkeypatch.setenv("PHOTON_CHANNELS", "imessage")
    monkeypatch.delenv("PHOTON_API_VERSION", raising=False)
    created = client.post("/link-codes", json={
        "case_id": "whatsapp-private-case", "channel": "whatsapp_business",
    }, headers=headers)
    assert created.status_code == 200
    link = created.json()
    assert re.fullmatch(r"BILLO-[A-Z2-9]{4}-[A-Z2-9]{4}", link["code"])
    assert link["channel"] == "whatsapp_business"
    assert "whatsapp-private-case" not in str(link)
    assert link["case_page"].endswith("/continue/" + link["code"])
    assert link["available"] is False
    assert link["deep_link"] == link["qr_url"] == ""

    status = client.get(f"/api/link/{link['code']}")
    assert status.status_code == 200
    assert status.headers["cache-control"].startswith("private, no-store")
    assert "case_id" not in status.json()
    assert status.json()["channel"] == "whatsapp_business"
    assert status.json()["code"] == status.json()["display_code"] == link["code"]
    assert status.json()["available"] == link["available"]

    wrong_channel = client.post("/link/claim", json={
        "code": link["code"], "handle_hash": "first-handle", "space_id": "first-space",
        "channel": "imessage",
    }, headers=headers).json()
    first = client.post("/link/claim", json={
        "code": link["code"], "handle_hash": "first-handle", "space_id": "first-space",
        "channel": "whatsapp_business",
    }, headers=headers).json()
    replay = client.post("/link/claim", json={
        "code": link["code"], "handle_hash": "other-handle", "space_id": "other-space",
    }, headers=headers).json()
    assert wrong_channel == {"status": "channel_mismatch", "case_id": ""}
    assert first == {"status": "linked", "case_id": "whatsapp-private-case"}
    assert replay == {"status": "used", "case_id": ""}


def test_whatsapp_handoff_requires_enabled_legacy_transport(monkeypatch):
    monkeypatch.setenv("PHOTON_WHATSAPP_ADDRESS", "+14155550123")
    monkeypatch.setenv("PHOTON_CHANNELS", "imessage,whatsapp_business")
    monkeypatch.delenv("PHOTON_API_VERSION", raising=False)
    enabled = client.post("/link-codes", json={
        "case_id": "whatsapp-transport-case", "channel": "whatsapp_business",
    }, headers=headers).json()
    assert enabled["available"] is True
    assert enabled["deep_link"].startswith("https://wa.me/14155550123?")

    monkeypatch.setenv("PHOTON_API_VERSION", "beta")
    beta = client.post("/link-codes", json={
        "case_id": "whatsapp-beta-case", "channel": "whatsapp_business",
    }, headers=headers).json()
    assert beta["available"] is False
    assert beta["deep_link"] == beta["qr_url"] == ""


def test_new_link_code_expires_prior_waiting_code_for_same_case_and_channel():
    body = {"case_id": "replacement-code-case", "channel": "imessage"}
    old = client.post("/link-codes", json=body, headers=headers).json()
    new = client.post("/link-codes", json=body, headers=headers).json()
    assert old["code"] != new["code"]
    assert client.get(f"/api/link/{old['code']}").json()["status"] == "expired"
    rejected = client.post("/link/claim", json={
        "code": old["code"], "handle_hash": "old-handle", "space_id": "old-space",
        "channel": "imessage",
    }, headers=headers).json()
    assert rejected == {"status": "expired", "case_id": ""}
    assert main.store.case_for_handle("old-handle") is None


def test_missing_document_is_not_implicitly_replaced_by_demo():
    result = client.post("/reader/extract", json={"case_id": "missing-upload"}, headers=headers)
    assert result.status_code == 422
    assert "Attach a bill" in result.json()["detail"]


def test_multi_unit_line_total_is_not_multiplied_twice():
    request_id = start_operation("quantity-total", "after_care", "quantity-total-request")
    result = client.post("/after-care/organize", json={
        "case_id": "quantity-total", "request_id": request_id, "lines": [
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
    request_id = start_operation("real-image", "after_care", "real-image-organize")
    organized = client.post("/after-care/organize", json={
        "case_id": "real-image", "request_id": request_id, "lines": bill["lines"],
    }, headers=headers)
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
