"""Short, scan-friendly copy for Billo's Photon/iMessage door.

ASI:One keeps the detailed case record. iMessage gets the same decisions in a
compact form: one headline, the essential numbers, and one clear next action.
"""
from __future__ import annotations


def care_matches(places: list[dict]) -> str:
    lines = ["✨ Best care matches"]
    for index, place in enumerate(places, 1):
        kind = str(place.get("kind", "care")).replace("_", " ")
        lines.append(
            f"{index} · {place['name']} — ~${float(place['price_typical']):,.0f}"
            f"\n   {kind} · {place['hours']}"
        )
    lines.append("Reply @Billo book 1, 2, or 3")
    return "\n".join(lines)


def booking_saved(place: dict, amount: float, calendar_url: str) -> str:
    return "\n".join([
        "✅ Care plan saved",
        str(place["name"]),
        f"Estimate · ${amount:,.0f}",
        f"📅 {calendar_url}",
        "At the visit: @Billo + what they did",
    ])


def benefits(paths: list[dict]) -> str:
    if not paths:
        return "No matching benefit path yet. Tell @Billo which plan you have."
    lines = ["💸 Possible money-back paths"]
    lines.extend(f"• {path['name']} — needs {path['needed']}" for path in paths)
    lines.append("Possible—not guaranteed. Check your plan deadline.")
    return "\n".join(lines)


def organized_bill(
    *,
    kind: str,
    total: float,
    reader: str,
    provider_match: bool,
    estimate_amount: float | None,
    estimate_difference: float | None,
    unreviewed_lines: int,
    needs_review: list[int],
    payment_status: str,
) -> str:
    lines = [f"✅ {kind.title()} organized · ${total:,.2f}"]
    reader_line = {
        "ocr": "OCR · total verified",
        "vision": "Vision fallback · numbers cross-checked",
        "demo": "Demo document · simulated result",
        "demo_fallback": "Demo only · resend a clearer photo",
    }.get(reader, "Reader · review result")
    lines.append(reader_line)
    lines.append("Provider match · yes" if provider_match else "Provider match · review needed")
    if estimate_amount is not None:
        difference = float(estimate_difference or 0)
        sign = "+" if difference > 0 else ""
        lines.append(f"Estimate ${estimate_amount:,.2f} → bill ${total:,.2f} ({sign}${difference:,.2f})")
    if unreviewed_lines:
        lines.append(f"⚠️ {unreviewed_lines} uncoded charge(s) need review")
    if needs_review:
        numbers = ", ".join(str(number) for number in needs_review)
        lines.append(f"⚠️ Verify line(s) {numbers}")
    if payment_status == "unpaid":
        lines.append("Next · @Billo scan clinic QR")
    elif payment_status == "paid":
        lines.append("Next · @Billo check my HSA or insurance")
    else:
        lines.append("Next · @Billo this is paid / unpaid")
    return "\n".join(lines)
