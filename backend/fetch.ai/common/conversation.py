"""Deterministic small-talk handling; mixed symptom messages still use safety screening."""
from __future__ import annotations

import re

WELCOME = (
    "👋 Hi, I'm Billo\n\nMake every care dollar count.\n\n"
    "I can compare care prices, organize bills and receipts, and explore possible benefits.\n"
    "Try: find care near UCLA, or attach a receipt and say whether it is paid.\n\n"
    "On WhatsApp, start each request with @Billo. Payments are simulated.\n"
    "More about Billo\nhttps://www.getbillo.us"
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
        return "You're welcome. Send your next care question, or attach a bill or receipt when you're ready."
    if clean in {"bye", "goodbye", "see you"}:
        return "Take care. Send STOP if you want to stop reminders."
    if clean in {"tell me a joke", "write me a poem", "what is the weather", "what's the weather"}:
        return "I'm focused on healthcare costs: comparing care prices, organizing receipts, and exploring possible benefits. What would you like help with?"
    if clean in {"yes", "no", "y", "n"} and not (stage == "booked" and asked):
        return "What would you like to do next? You can find care, attach a receipt, or ask about a benefit."
    if clean in {"bill", "receipt", "unpaid bill", "paid receipt", "i have a bill", "i have a receipt", "upload bill", "upload receipt", "check my bill", "read my bill", "check this bill", "here is my bill", "check my receipt", "read my receipt", "check this receipt", "here is my receipt", "can you check my bill", "can you read my receipt"}:
        return "Attach a clear bill or receipt photo or PDF. In the caption, say 'paid receipt' or 'unpaid bill'. On WhatsApp, include @Billo."
    if clean in {"pay", "pay bill", "pay my bill", "payment"}:
        return "Start by attaching the unpaid final bill. After it is organized, ask 'scan clinic QR'. Billo checks the clinic and amount before asking for explicit approval. Payments are simulated; no real money moves."
    if clean in {"reimburse", "reimbursement", "refund", "money back"}:
        return "Attach your paid receipt first, then name your actual plan, such as HSA or FSA. A possible benefit is not an approval. Reimbursement requires administrator approval and your explicit consent; payouts are simulated."
    if clean in {"status", "my status", "what next", "what's next"}:
        steps = {
            "new": "Tell me what care you need and your city or ZIP code, or attach a bill or receipt.",
            "choosing": "Review the care options, then reply 'book 1' with your chosen option number.",
            "booked": "Your care plan and estimate are saved. This is not a clinic-confirmed appointment. Log services during your visit or send the final bill afterward.",
            "organizing": "Your document is being organized. Wait for its result before approving any next step.",
            "organized": "Your document record is organized. Review any flagged items, then check your named benefit or request a clinic QR review for an unpaid bill.",
            "settled": "Review the settlement result above. A simulated payment or reimbursement does not mean real money moved.",
            "emergency": "Your earlier message triggered the emergency safety check. If this is an emergency, call 911. Billo is not an emergency service.",
        }
        return steps.get(stage, "Send 'help' to see what Billo can do. No payment is approved by asking for status.")
    if clean in {"this is paid", "this is unpaid", "it is paid", "it is unpaid"}:
        return "Please resend the document with 'paid receipt' or 'unpaid bill' in its caption so I can update the correct record."
    return None
