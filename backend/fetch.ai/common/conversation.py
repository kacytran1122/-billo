"""Deterministic small-talk handling; mixed symptom messages still use safety screening."""
from __future__ import annotations

import re

WELCOME = (
    "Hi — I’m Billo, your care-cost assistant.\n\n"
    "I can help you:\n"
    "• compare care options and estimated prices by location\n"
    "• organize a bill or receipt\n"
    "• review possible benefit and reimbursement paths\n\n"
    "To begin, describe what happened and include your city or ZIP code. You can also attach a bill or receipt and label it paid or unpaid.\n\n"
    "In one-to-one chats, no tag is needed. In group chats, mention @Billo.\n\n"
    "Billo is not an emergency service or a substitute for medical, legal, insurance, or financial advice. Payment features are simulations.\n"
    "Learn more: https://www.getbillo.us"
)


def normalize_request(text: str) -> str:
    return re.sub(r"^@(?:getbillo|billo)\b\s*", "", text.strip(), flags=re.I).strip()


def payment_status(text: str) -> str:
    low = text.lower()
    # Unpaid must win: 'unpaid receipt' contains the substring 'paid receipt'.
    if re.search(r"\b(?:unpaid|not paid|haven't paid|have not paid|amount due|i owe)\b", low):
        return "unpaid"
    if re.search(r"\b(?:paid receipt|already paid|i paid|payment confirmation)\b", low):
        return "paid"
    return "unknown"


def quick_reply(text: str, *, has_files: bool = False, stage: str = "new", asked: bool = False) -> str | None:
    if has_files:
        return None  # A greeting in an upload caption must not swallow the document.
    clean = normalize_request(text).lower().replace("’", "'")
    clean = re.sub(r"[!?. ,]+$", "", clean)
    if clean in {"", "hi", "hello", "hey", "hiya", "hi there", "hello there", "hey there", "hi billo", "hello billo", "hey billo", "good morning", "good afternoon", "good evening", "👋", "xin chào", "chào billo"}:
        return WELCOME
    if clean in {"help", "start", "menu", "features", "?", "what can you do", "what can you help me with", "how does this work", "how do you work", "what is billo", "who are you", "how are you", "how can you help"} or re.fullmatch(r"(?:hi|hey|hello)(?: billo)?[,!.\s]+(?:what can you do|who are you|how can you help|how are you)", clean):
        return WELCOME
    if clean in {"thanks", "thank you", "thank you billo", "ty", "awesome", "great", "ok", "okay"}:
        return "You’re welcome. When you’re ready, ask another care-cost question or attach a bill or receipt."
    if clean in {"bye", "goodbye", "see you"}:
        return "Take care. You can return at any time. Send STOP to turn off reminders for this case."
    if clean in {"tell me a joke", "write me a poem", "what is the weather", "what's the weather"}:
        return "I’m designed for care-cost questions, bill and receipt organization, and possible benefit paths. What would you like help with?"
    if clean in {"yes", "no", "y", "n"} and not (stage == "booked" and asked):
        return "What would you like to do next? You can compare care options, attach a bill or receipt, or ask about a benefit."
    if clean in {"bill", "receipt", "unpaid bill", "paid receipt", "i have a bill", "i have a receipt", "upload bill", "upload receipt", "check my bill", "read my bill", "check this bill", "here is my bill", "check my receipt", "read my receipt", "check this receipt", "here is my receipt", "can you check my bill", "can you read my receipt"}:
        return "Attach a clear photo or PDF, then label it ‘paid receipt’ or ‘unpaid bill.’ In a one-to-one chat, you do not need to tag Billo."
    if clean in {"pay", "pay bill", "pay my bill", "payment"}:
        return "First, attach the unpaid final bill. After I organize it, send ‘scan clinic QR.’ I’ll verify the clinic and amount before requesting explicit approval. This is a simulation: no card data is collected and no money moves."
    if clean in {"reimburse", "reimbursement", "refund", "money back"}:
        return "First, attach the paid receipt and name the benefit you actually have, such as an HSA or FSA. A possible path is not confirmation of eligibility. Reimbursement requires administrator approval and your explicit consent; payouts are simulated."
    if clean in {"status", "my status", "what next", "what's next"}:
        steps = {
            "new": "Next step: describe the care you need and include your city or ZIP code, or attach a bill or receipt.",
            "choosing": "Next step: review the options, then reply ‘book 1’ using the number you prefer. This saves a care plan; it does not confirm an appointment.",
            "booked": "Your selected care option and estimate are saved. The provider has not confirmed an appointment. You can log services during the visit or send the final bill afterward.",
            "organizing": "I’m organizing your document now. Please wait for the result before approving a payment or reimbursement step.",
            "organized": "Your document is organized. Review any flagged items, then check a benefit you actually have or request QR review for an unpaid bill.",
            "settled": "Review the settlement result above. Any payment or reimbursement shown is a simulation; no real funds moved.",
            "emergency": "Your earlier message triggered the emergency safety check. If this is an emergency, call 911. Billo is not an emergency service.",
        }
        return steps.get(stage, "Send 'help' to see what Billo can do. No payment is approved by asking for status.")
    if clean in {"this is paid", "this is unpaid", "it is paid", "it is unpaid"}:
        return "Please resend the document and label it ‘paid receipt’ or ‘unpaid bill’ so I can create the correct record."
    return None
