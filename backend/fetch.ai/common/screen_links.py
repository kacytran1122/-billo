"""Route each response to the most relevant public demo screen.

These URLs never expose a patient's case. They are static, synthetic previews.
"""
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


def screen_for(text: str, stage: str = "new") -> str:
    """Choose by the result being shown, then by the user's likely next step."""
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
    if any(word in low for word in (
        "benefit", "reimburse", "hsa", "fsa", "hra", "coverage",
        "insurance", "claim", "money-back",
    )):
        return "benefits"
    if any(word in low for word in (
        "attach", "upload", "photo", "pdf", "document received", "paid receipt",
        "unpaid bill", "final bill",
    )):
        return "scan"
    if any(phrase in low for phrase in (
        "care plan saved", "care plan is saved", "saved estimate", "estimated price", "expected price",
    )):
        return "estimate"
    if any(phrase in low for phrase in (
        "visit log", "service received", "services you receive", "running estimate",
        "visit follow-up", "after the visit",
    )):
        return "visit"
    if stage == "organized":
        return "match"
    if stage == "booked":
        return "visit"
    return "prices"


def with_screen_link(text: str, stage: str = "new") -> str:
    low = text.lower()
    if "https://www.getbillo.us/" in text or "call 911" in low or "988" in low or low.startswith(("stopped", "✅ stopped", "you are unsubscribed")):
        return text
    screen = screen_for(text, stage)
    return f"{text}\n\n{SCREENS[screen]} screen (demo, not your private record):\n{screen_url(screen)}"
