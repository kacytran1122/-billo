"""Deterministic small-talk handling; mixed symptom messages still use safety screening."""
from __future__ import annotations

import re

WELCOME = (
    "Hi, I’m Billo, your care-cost assistant.\n\n"
    "I can help you:\n"
    "• compare care options and estimated prices by location\n"
    "• organize a bill or receipt\n"
    "• review possible benefit and reimbursement paths\n\n"
    "To begin, describe what happened and include your city or ZIP code. You can also attach a bill or receipt and label it paid or unpaid.\n\n"
    "In one-to-one chats, no tag is needed. Messaging availability depends on the connected Billo channel.\n\n"
    "Billo is not an emergency service or a substitute for medical, legal, insurance, or financial advice. Payment features are simulations.\n\n"
    "Open the relevant demo screen:\n"
    "• Compare care: https://www.getbillo.us/tools/prices\n"
    "• Organize a bill or receipt: https://www.getbillo.us/tools/scan\n"
    "• Review payment safeguards: https://www.getbillo.us/tools/payment\n"
    "Website screens are interactive demos, not your private case record."
)

FOCUS_REPLY = (
    "I’m a healthcare cost and after-care assistant. I can compare location-matched care estimates, "
    "organize bills or receipts, and explain possible benefit paths. I can’t help with unrelated "
    "topics. Tell me what care you need and your city or ZIP code, or attach a bill or receipt."
)

_OUT_OF_SCOPE_RE = re.compile(
    r"\b(?:weather|forecast|joke|poem|song|lyrics|recipe|restaurant|hotel|flight|vacation|"
    r"sports?|score|stock|crypto|president|election|politics|homework|essay|translate|translation|"
    r"write (?:code|a program)|debug (?:code|my app)|programming)\b",
    re.I,
)

SCOPE_REPLY = (
    "I can help with care options and estimated costs, visit preparation, medical bills and receipts, "
    "and possible reimbursement paths. I can’t help with unrelated tasks or diagnose a condition.\n\n"
    "Tell me what care you need and your city or ZIP code, or attach a bill or receipt."
)


def clinical_advice_request(text: str) -> bool:
    """These requests need a clinician, not an invented diagnosis or dosage."""
    return bool(re.search(
        r"\b(?:diagnos\w*|prescrib\w*|dosage|what (?:disease|illness)|"
        r"(?:should|can) i take|how (?:much|many) .{0,35}(?:take|pills|tablets)|"
        r"(?:stop|change|increase|decrease) my (?:medication|dose)|treatment plan)\b", text, re.I
    ))


def care_request(text: str, *, has_prior: bool = False) -> bool:
    """Conservative scope gate; unknown text gets clarification, not a default knee search."""
    if clinical_advice_request(text):
        return True  # Still run the emergency screen before giving the boundary response.
    return bool(re.search(
        r"\b(?:care|clinic\w*|hospital\w*|doctor\w*|physician|provider|urgent|emergency|er|"
        r"medical|health\w*|visit|appointment|"
        r"bill\w*|receipt\w*|insurance|benefit\w*|reimburse\w*|deductible|copay|coinsurance|"
        r"pain\w*|hurt\w*|ache\w*|injur\w*|broke\w*|broken|fractur\w*|sprain\w*|"
        r"swollen|swelling|fever|cough\w*|rash|sick|nausea|vomit\w*|dizz\w*|"
        r"bleed\w*|breath\w*|choking|numb\w*|fainted|passed out|unconscious|"
        r"crushing|face drooping|slurred|confused|kill myself|suicide|end my life|"
        r"head|knee|ankle|leg|arm|chest|stomach|throat|tooth|dental|pregnan\w*|"
        r"allerg\w*|burn\w*|cut|wound|infection|mental|therapy|vaccine|x.?ray)\b", text, re.I
    )) or bool(has_prior and re.search(r"\b(?:near|in|zip|location|chicago|ucla|westwood|los angeles)\b|\b\d{5}\b", text, re.I))


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
    explanations = {
        "what is a deductible": "A deductible is the amount you may need to pay for covered care before your plan begins sharing certain costs. Some services are covered earlier. Check your plan documents for the exact rules.",
        "what is a copay": "A copay is a fixed amount you pay for a covered service. It can vary by provider and service, and a deductible may still apply. Check your plan’s summary of benefits.",
        "what is coinsurance": "Coinsurance is your percentage of an allowed charge for covered care, often after your deductible. Your plan and network status determine the actual amount.",
        "what is an eob": "An Explanation of Benefits explains how your insurer processed a claim. It is not a bill. Compare its patient-responsibility amount with the provider’s bill before paying.",
        "what is an itemized bill": "An itemized bill lists individual services, dates, codes, and charges. Ask the provider for one if your statement only shows a total. I can help organize a clear photo or PDF.",
        "can you guarantee reimbursement": "No. I can organize supporting documents and identify possible benefit paths. Your insurer or benefit administrator decides eligibility and reimbursement. Any payout here is a simulation.",
        "is my information private": "Share only the information needed for the task. Redact Social Security numbers, card details, and unrelated medical information. Group members can see messages sent in a group. Do not send passwords or API keys.",
        "what is prior authorization": "Prior authorization is a plan review that may be required before certain care, tests, or medicines. It is not a guarantee of coverage or payment. Ask the provider and your plan whether it is required and obtain the decision in writing.",
        "what is in network": "An in-network provider has a contracted rate with your plan. Network participation can differ by clinician, facility, and service, so verify all three with your plan before care.",
        "what is out of network": "Out-of-network care may have higher cost sharing, a separate deductible, or no coverage. Ask your plan for the allowed amount and whether balance billing may apply.",
        "what is balance billing": "Balance billing is when a provider bills you for the difference between its charge and the amount your plan recognizes. Rules and protections vary, so compare the provider bill with your EOB and contact your plan before paying a disputed amount.",
        "what is a good faith estimate": "A Good Faith Estimate is an advance estimate of expected charges for scheduled care, generally for people who are uninsured or not using insurance. It is not a final bill; ask the provider what services and clinicians are included.",
    }
    if clean in explanations:
        return explanations[clean]
    if clean in {"", "hi", "hello", "hey", "hiya", "hi there", "hello there", "hey there", "hi billo", "hello billo", "hey billo", "good morning", "good afternoon", "good evening", "👋", "xin chào", "chào billo"}:
        return WELCOME
    if clean in {"help", "start", "menu", "features", "?", "what can you do", "what can you help me with", "how does this work", "how do you work", "what is billo", "who are you", "how are you", "how can you help"} or re.fullmatch(r"(?:hi|hey|hello)(?: billo)?[,!.\s]+(?:what can you do|who are you|how can you help|how are you)", clean):
        return WELCOME
    if clean in {"thanks", "thank you", "thank you billo", "ty", "awesome", "great", "ok", "okay"}:
        return "You’re welcome. When you’re ready, ask another care-cost question or attach a bill or receipt."
    if clean in {"bye", "goodbye", "see you"}:
        return "Take care. You can return at any time. Send STOP to turn off reminders for this case."
    if _OUT_OF_SCOPE_RE.search(clean) and not care_request(clean):
        return FOCUS_REPLY
    if clean in {"test", "testing", "huh", "what", "why", "maybe", "idk", "i don't know", "anything", "random"}:
        return "I’m not sure what healthcare task you want to complete. Describe the care you need and include your city or ZIP code, or attach a bill or receipt."
    if clean in {"yes", "no", "y", "n"} and not (stage == "booked" and asked):
        return "What would you like to do next? You can compare care options, attach a bill or receipt, or ask about a benefit."
    if clean in {"bill", "receipt", "unpaid bill", "paid receipt", "i have a bill", "i have a receipt", "upload bill", "upload receipt", "check my bill", "read my bill", "check this bill", "here is my bill", "check my receipt", "read my receipt", "check this receipt", "here is my receipt", "can you check my bill", "can you read my receipt"}:
        return "Attach a clear photo or PDF, then label it ‘paid receipt’ or ‘unpaid bill.’ In a one-to-one chat, you do not need to tag Billo."
    if clean in {"pay", "pay bill", "pay my bill", "payment"}:
        return "First, attach the unpaid final bill. After I organize it, send ‘scan clinic QR.’ I’ll verify the clinic and amount before requesting explicit approval. This is a simulation: no card data is collected and no money moves."
    if clean in {"reimburse", "reimbursement", "refund", "money back"}:
        return "First, attach the paid receipt and name the benefit you actually have, such as an HSA or FSA. A possible path is not confirmation of eligibility. Reimbursement requires administrator approval and your explicit consent; payouts are simulated."
    if re.search(r"\b(?:claim (?:was |is )?(?:denied|rejected)|denied claim|appeal (?:a |my )?claim)\b", clean):
        return "Start with the denial notice, EOB, itemized bill, and the plan’s appeal instructions. Check the filing deadline and stated denial reason. I can organize those documents, but your plan decides the appeal."
    if re.search(r"\b(?:financial assistance|charity care|payment plan|can't afford|cannot afford)\b", clean):
        return "Ask the provider for its financial-assistance policy, application, income rules, and an interest-free payment-plan option before using credit. I can help organize the bill, but the provider decides assistance."
    if re.search(r"\b(?:schedule|reschedule|cancel|confirm) (?:an |my |the )?(?:appointment|visit)\b", clean):
        return "Billo can save a care option and estimate, but it cannot confirm, reschedule, or cancel an appointment. Contact the provider directly and verify the time, location, availability, and price; only add a confirmed time to your calendar."
    if re.fullmatch(r"(?:can you |do you |please )?(?:help|explain|check|review)?\s*(?:with\s+)?(?:my\s+)?(?:insurance|benefits?|coverage|claim)", clean):
        return "I can review possible benefit paths after you attach the bill or paid receipt and name the plan you actually have. I can’t confirm coverage, eligibility, or claim approval; verify those decisions with the plan administrator."
    if clean in {"status", "my status", "what next", "what's next"}:
        steps = {
            "new": "Next step: describe the care you need and include your city or ZIP code, or attach a bill or receipt.",
            "choosing": "Next step: review the options, then reply ‘book 1’ using the number you prefer. This saves a care plan; it does not confirm an appointment.",
            "booked": "Your selected care option and estimate are saved. The provider has not confirmed an appointment. You can log services during the visit or send the final bill afterward.",
            "during": "Your visit log is active. Send each service you receive to update the running estimate, or attach the final bill afterward.",
            "organizing": "I’m organizing your document now. Please wait for the result before approving a payment or reimbursement step.",
            "organized": "Your document is organized. Review any flagged items, then check a benefit you actually have or request QR review for an unpaid bill.",
            "settled": "Review the settlement result above. Any payment or reimbursement shown is a simulation; no real funds moved.",
            "emergency": "Your earlier message triggered the emergency safety check. If this is an emergency, call 911. Billo is not an emergency service.",
        }
        return steps.get(stage, "Send 'help' to see what Billo can do. No payment is approved by asking for status.")
    if clean in {"this is paid", "this is unpaid", "it is paid", "it is unpaid"}:
        return "Please resend the document and label it ‘paid receipt’ or ‘unpaid bill’ so I can create the correct record."
    return None
