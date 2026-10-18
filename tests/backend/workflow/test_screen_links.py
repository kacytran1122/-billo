import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/fetch.ai"))
from common.screen_links import SCREENS, screen_for, with_screen_link


@pytest.mark.parametrize("text,stage,screen", [
    ("Compare care near your city", "new", "prices"),
    ("Your care plan is saved", "booked", "estimate"),
    ("Attach your paid receipt", "new", "scan"),
    ("Review the matched charges", "organized", "match"),
    ("Scan clinic QR", "organized", "payment"),
    ("Possible HSA benefit paths", "organized", "benefits"),
])
def test_task_specific_links_use_existing_screen_names(text, stage, screen):
    linked = with_screen_link(text, stage)
    assert linked.endswith(f"/tools/{screen}")
    assert "not your private record" in linked
    assert screen in SCREENS
    assert with_screen_link(linked, stage) == linked


@pytest.mark.parametrize("text", ["Call 911 now.", "Stopped. Reminders canceled.", "✅ Stopped. Reminders canceled.", "You are unsubscribed."])
def test_emergency_and_opt_out_messages_do_not_receive_extra_links(text):
    assert with_screen_link(text) == text


def test_completed_bill_review_wins_over_generic_benefit_wording():
    text = "Document review complete. Benefit review: name a benefit you actually have."
    assert screen_for(text, "organized") == "match"


def test_unsaved_care_options_link_to_comparison_instead_of_saved_estimate():
    text = (
        "Location: Chicago, IL\n"
        "Care options (3):\n"
        "1. Chicago Urgent Care (demo)\n"
        "Estimated price: $260 (from $190)\n"
        "Next step: reply 'book 1' to save an option and estimate."
    )
    linked = with_screen_link(text, "choosing")
    assert "Care comparison screen" in linked
    assert linked.endswith("/tools/prices")


def test_booked_stage_routes_the_next_step_to_the_visit_log():
    assert screen_for("Tell me what service you received.", "booked") == "visit"
