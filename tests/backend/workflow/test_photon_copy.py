import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "fetch.ai"))

from common.photon_copy import benefits, booking_saved, care_matches, organized_bill


def test_care_matches_is_short_and_has_one_tagged_action():
    text = care_matches([
        {"name": "Campus Health", "kind": "clinic", "price_typical": 180, "hours": "open until 6 pm"},
        {"name": "Westwood Urgent", "kind": "urgent_care", "price_typical": 240, "hours": "open until 9 pm"},
    ])
    assert text.startswith("📍 Your care shortlist\n\n")
    assert "1. Campus Health\n   ~$180 estimated" in text
    assert text.endswith("Reply @Billo book 1 (or another option number)")
    assert len(text) < 500


def test_booking_copy_keeps_amount_calendar_and_tagged_next_action():
    text = booking_saved({"name": "Westwood Urgent"}, 240, "https://api.getbillo.us/calendar/demo.ics")
    assert "Estimate · $240" in text
    assert "https://api.getbillo.us/calendar/demo.ics" in text
    assert text.endswith("At the visit: @Billo + what they did")


def test_organized_ocr_bill_shows_confidence_and_next_action():
    text = organized_bill(
        kind="unpaid final bill",
        total=360,
        reader="ocr",
        provider_match=True,
        estimate_amount=240,
        estimate_difference=120,
        unreviewed_lines=1,
        needs_review=[],
        payment_status="unpaid",
    )
    assert "Read with OCR · review extracted amounts" in text
    assert "Estimate $240.00 → bill $360.00 (+$120.00)" in text
    assert "⚠️ 1 uncoded charge(s) need review" in text
    assert text.endswith("Next · @Billo scan clinic QR")


def test_vision_review_and_paid_benefit_action_are_clear():
    text = organized_bill(
        kind="paid receipt",
        total=120,
        reader="vision",
        provider_match=False,
        estimate_amount=None,
        estimate_difference=None,
        unreviewed_lines=0,
        needs_review=[2, 4],
        payment_status="paid",
    )
    assert "Read with vision · review extracted amounts" in text
    assert "Provider match · review needed" in text
    assert "⚠️ Verify line(s) 2, 4" in text
    assert text.endswith("Next · @Billo check my HSA or insurance")


def test_benefit_copy_is_explicitly_not_a_promise():
    text = benefits([{"name": "HSA", "needed": "itemized receipt"}])
    assert "• HSA\n  Needs: itemized receipt" in text
    assert "Eligibility is not confirmed" in text


def test_care_match_actions_never_reference_missing_options():
    assert "No care matches yet" in care_matches([])
    text = care_matches([{"name": "Clinic", "kind": "clinic", "price_typical": 120, "hours": "9–5"}])
    assert text.endswith("Reply @Billo book 1")


def test_demo_results_are_not_presented_as_verified_ocr():
    text = organized_bill(kind="receipt", total=100, reader="demo_fallback", provider_match=False,
                          estimate_amount=None, estimate_difference=None, unreviewed_lines=0,
                          needs_review=[], payment_status="unknown")
    assert "Demo only" in text
    assert "Provider match · review needed" in text
    assert "total verified" not in text
