"""Short, scan-friendly copy for Billo's Photon messaging channels.

ASI:One keeps the detailed case record. WhatsApp gets the same decisions in a
compact form: one headline, the essential numbers, and one clear next action.
"""
from __future__ import annotations

from .screen_links import screen_url, visit_url_for_stage


def care_matches(places: list[dict], location: str = "") -> str:
    if not places:
        return "No verified care options found for that location.\n\nTry another city or ZIP code:\n@Billo find care near [ZIP]"
    heading = "📍 Your care shortlist" + (f" — {location}" if location else "")
    lines = [heading, "", "Demo estimates · confirm price and availability with the provider", ""]
    for index, place in enumerate(places, 1):
        kind = str(place.get("kind", "care")).replace("_", " ")
        lines.append(
            f"{index}. {place['name']}\n"
            f"   ~${float(place['price_typical']):,.0f} estimated · {kind}\n"
            f"   {place['hours']}\n"
            f"   {place.get('address', '')}\n"
        )
    lines.append("Next: @Billo book 1" if len(places) == 1 else "Next: @Billo book 1 (or another option number)")
    lines.append("Saving an option does not confirm an appointment.")
    lines.append(f"Compare care (demo): {screen_url('prices')}")
    return "\n".join(lines)


def booking_saved(place: dict, amount: float, calendar_url: str = "", visit_url: str = "") -> str:
    lines = [
        "Care plan saved",
        "",
        str(place["name"]),
    ]
    if place.get("address"):
        lines.append(str(place["address"]))
    if place.get("hours"):
        lines.append(str(place["hours"]))
    lines.extend([
        f"Estimated price · ${amount:,.0f}",
        "Appointment not confirmed",
    ])
    if calendar_url:
        lines.append(f"📅 {calendar_url}")
    else:
        lines.append("No appointment time saved")
    lines.extend(["", "At the visit: send @Billo and the service received"])
    if visit_url:
        lines.append(f"Open your private visit page: {visit_url_for_stage(visit_url, 'booked')}")
    else:
        lines.append(f"Review the saved estimate (demo): {screen_url('estimate')}")
    return "\n".join(lines)


def benefits(paths: list[dict], visit_url: str = "") -> str:
    if not paths:
        return "No matching benefit path found. Tell @Billo which plan or benefit you actually have."
    lines = ["💸 Explore money-back options", ""]
    lines.extend(f"• {path['name']}\n  Needs: {path['needed']}\n" for path in paths)
    lines.append("Eligibility is not confirmed. Check your plan deadline.")
    lines.append("Next: @Billo check my benefits")
    if visit_url:
        lines.append(f"Open your bill summary: {visit_url_for_stage(visit_url, 'organized')}")
    else:
        lines.append(f"Review benefit paths (demo): {screen_url('benefits')}")
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
    visit_url: str = "",
) -> str:
    lines = [f"🧾 {kind.title()} organized", "", f"Total · ${total:,.2f}"]
    reader_line = {
        "ocr": "Read with OCR · review extracted amounts",
        "vision": "Read with vision · review extracted amounts",
        "demo": "Demo document · simulated result",
        "demo_fallback": "Demo only · resend a clearer photo",
    }.get(reader, "Reader · review result")
    lines.append(reader_line)
    lines.append("Provider matches visit record" if provider_match else "Provider match · review needed")
    if estimate_amount is not None:
        difference = float(estimate_difference or 0)
        sign = "+" if difference > 0 else ""
        lines.append(f"Estimate ${estimate_amount:,.2f} → bill ${total:,.2f} ({sign}${difference:,.2f})")
    if unreviewed_lines:
        lines.append(f"⚠️ {unreviewed_lines} uncoded charge(s) need review")
    if needs_review:
        numbers = ", ".join(str(number) for number in needs_review)
        lines.append(f"⚠️ Verify line(s) {numbers}")
    lines.append("")
    if payment_status == "unpaid":
        lines.append("Next · @Billo scan clinic QR")
    elif payment_status == "paid":
        lines.append("Next · @Billo check my HSA or insurance")
    else:
        lines.append("Next · @Billo this is paid / unpaid")
    if visit_url:
        lines.append(f"Open your bill summary: {visit_url_for_stage(visit_url, 'organized')}")
    else:
        lines.append(f"Review the organized charges (demo): {screen_url('match')}")
    return "\n".join(lines)
