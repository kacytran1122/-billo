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
    assert text.startswith("✨ Best care matches")
    assert "1 · Campus Health — ~$180" in text
    assert text.endswith("Reply @Billo book 1, 2, or 3")
    assert len(text.splitlines()) == 6


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
    assert "OCR · total verified" in text
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
    assert "Vision fallback · numbers cross-checked" in text
    assert "Provider match · review needed" in text
    assert "⚠️ Verify line(s) 2, 4" in text
    assert text.endswith("Next · @Billo check my HSA or insurance")


def test_benefit_copy_is_explicitly_not_a_promise():
    text = benefits([{"name": "HSA", "needed": "itemized receipt"}])
    assert "• HSA — needs itemized receipt" in text
    assert "Possible—not guaranteed" in text
