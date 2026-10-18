"""Route responses to a relevant screen without exposing an internal case id.

Before a care plan is saved, links point to public synthetic previews. Once Core
has issued an opaque case URL, the same stable URL follows the conversation
through the booked, during-visit and after-care views.
"""
from __future__ import annotations

import re


BASE = "https://www.getbillo.us/tools/"
SCREENS = {
    "prices": "Care comparison",
    "estimate": "Saved estimate",
    "visit": "Visit log",
    "scan": "Bill and receipt",
    "match": "Bill review",
    "payment": "Clinic QR and payment simulation",
    "benefits": "Benefit paths",
}


def screen_url(screen: str) -> str:
    return f"{BASE}{screen}"


def visit_url_for_stage(visit_url: str, stage: str) -> str:
    """Return the stable case URL at the section represented by ``stage``."""
    base = visit_url.split("#", 1)[0].rstrip("/")
    if stage == "during":
        return f"{base}#during"
    if stage in {"organizing", "organized", "settled"}:
        return f"{base}#after"
    return base


def screen_for(text: str, stage: str = "new") -> str | None:
    """Choose a screen only when the response describes a concrete workflow."""
    low = text.lower()
    if any(phrase in low for phrase in (
        "document review complete", "bill organized", "receipt organized",
        "provider match", "unreviewed", "line-by-line", "matched charges",
    )):
        return "match"
    if any(phrase in low for phrase in (
        "clinic qr", "wallet", "payment simulation", "qr verification",
        "qr verified", "visa demo", "payment review", "no money moved",
    )):
        return "payment"
    if any(phrase in low for phrase in (
        "explore money-back options", "i found possible benefit paths",
        "eligibility is not confirmed", "possible, not confirmed",
        "review benefit paths", "possible hsa benefit paths",
    )):
        return "benefits"
    if any(phrase in low for phrase in (
        "attach a clear", "attach your", "please attach", "document received",
        "i don’t see an attached document", "send the final bill",
        "bill and receipt screen",
    )):
        return "scan"
    if any(phrase in low for phrase in (
        "care plan saved", "care plan is saved", "saved estimate", "estimate saved",
    )):
        return "estimate"
    if any(phrase in low for phrase in (
        "visit log", "service received", "service you received", "services you receive", "running estimate",
        "visit follow-up", "after the visit",
    )):
        return "visit"
    if any(phrase in low for phrase in (
        "your care shortlist", "care options (", "care comparison screen",
        "compare care near", "no verified care options",
    )):
        return "prices"
    if stage == "organized" and any(phrase in low for phrase in (
        "your document is organized", "organized charges", "flagged items",
    )):
        return "match"
    if stage in {"booked", "during"} and any(phrase in low for phrase in (
        "selected care option and estimate are saved", "visit log is active",
    )):
        return "visit"
    return None


def with_screen_link(text: str, stage: str = "new", visit_url: str = "") -> str:
    low = text.lower()
    if "call 911" in low or "988" in low or low.startswith(("stopped", "✅ stopped", "you are unsubscribed")):
        return text
    screen = screen_for(text, stage)
    if screen is None:
        return text
    if visit_url and stage in {"booked", "during", "organizing", "organized", "settled"}:
        # Legacy copy sometimes carried a public /tools demo URL. A private case
        # view supersedes it; keep one relevant destination in the response.
        text = "\n".join(
            line for line in text.splitlines()
            if "https://www.getbillo.us/tools/" not in line
        ).rstrip()
        target = visit_url_for_stage(visit_url, stage)
        base = visit_url.split("#", 1)[0].rstrip("/")
        # A compact channel-specific response may already carry the case link.
        # If it has an older section anchor, advance it instead of duplicating it.
        pattern = rf"{re.escape(base)}(?:#[A-Za-z0-9_-]+)?"
        if re.search(pattern, text):
            return re.sub(pattern, target, text)
        label = {
            "during": "Open your live visit page",
            "organizing": "Open your private visit page",
            "organized": "Open your bill summary",
            "settled": "Open your bill summary",
        }.get(stage, "Open your private visit page")
        return f"{text}\n\n{label} (private link — do not share):\n{target}"
    if "https://www.getbillo.us/" in text:
        return text
    return f"{text}\n\n{SCREENS[screen]} screen (demo, not your private record):\n{screen_url(screen)}"
