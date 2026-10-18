import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/fetch.ai"))
from common.screen_links import SCREENS, screen_for, with_screen_link
from common.conversation import WELCOME


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


@pytest.mark.parametrize("stage,suffix,text", [
    ("booked", "", "Care plan saved"),
    ("during", "#during", "Visit log updated"),
    ("organizing", "#after", "Document received"),
    ("organized", "#after", "Document review complete"),
    ("settled", "#after", "Visa wallet simulation ready"),
])
def test_private_case_link_follows_the_conversation_stage(stage, suffix, text):
    base = "https://www.getbillo.us/visit/opaque-case-token"
    linked = with_screen_link(text, stage, base)
    assert linked.endswith(base + suffix)
    assert linked.count(base) == 1
    assert "/tools/" not in linked


def test_private_case_link_replaces_old_anchor_and_legacy_demo_link():
    base = "https://www.getbillo.us/visit/opaque-case-token"
    text = f"Visit log updated\n{base}\nReview demo: https://www.getbillo.us/tools/visit"
    linked = with_screen_link(text, "during", base)
    assert linked.count(base) == 1
    assert f"{base}#during" in linked
    assert "/tools/visit" not in linked


@pytest.mark.parametrize("text", [
    "You’re welcome. When you’re ready, ask another care-cost question.",
    "I can’t help with unrelated topics. Tell me what healthcare task you need.",
    "A deductible is the amount you may need to pay before your plan shares costs.",
    "What would you like to do next?",
])
@pytest.mark.parametrize("stage", ["new", "booked", "organized"])
def test_unrelated_acknowledgements_and_explanations_do_not_get_a_screen_link(text, stage):
    visit_url = "https://www.getbillo.us/visit/opaque-case-token"
    assert screen_for(text, stage) is None
    assert with_screen_link(text, stage) == text
    assert with_screen_link(text, stage, visit_url) == text


@pytest.mark.parametrize("stage", ["booked", "organized"])
def test_help_keeps_its_complete_demo_menu_in_saved_cases(stage):
    assert with_screen_link(
        WELCOME, stage, "https://www.getbillo.us/visit/opaque-case-token",
    ) == WELCOME
