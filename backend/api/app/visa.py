"""Guarded Visa settlement helpers.

The QR path validates an EMV-style merchant-presented payload before creating a
wallet handoff. The reimbursement path records an approved Visa Direct payout.
Simulation mode is intentionally the only executable money mode until Visa onboarding
and product-specific payload certification are complete.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
from decimal import Decimal, InvalidOperation

from . import store


QR_MODE = os.getenv("VISA_QR_MODE", "simulate").strip().lower()
DIRECT_MODE = os.getenv("VISA_DIRECT_MODE", "simulate").strip().lower()
PUBLIC = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


def tlv(tag: str, value: str) -> str:
    value = str(value)
    if len(value) > 99:
        raise ValueError("EMV field is too long")
    return f"{tag}{len(value):02d}{value}"


def parse_tlv(payload: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    pos = 0
    while pos < len(payload):
        if pos + 4 > len(payload):
            raise ValueError("truncated EMV QR field")
        tag, size_text = payload[pos:pos + 2], payload[pos + 2:pos + 4]
        if not (tag.isdigit() and size_text.isdigit()):
            raise ValueError("invalid EMV QR tag or length")
        size = int(size_text)
        start, end = pos + 4, pos + 4 + size
        if end > len(payload):
            raise ValueError("truncated EMV QR value")
        fields[tag] = payload[start:end]
        pos = end
    return fields


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def demo_qr(provider: str, amount: float, invoice: str = "BILLO-DEMO") -> str:
    merchant = re.sub(r"[^A-Z0-9 .&-]", "", provider.upper())[:25] or "DEMO CARE CLINIC"
    merchant_id = hashlib.sha256(merchant.encode()).hexdigest()[:12].upper()
    account = tlv("00", "VISA") + tlv("01", merchant_id)
    extra = tlv("01", invoice[:25])
    base = "".join([
        tlv("00", "01"), tlv("01", "12"), tlv("26", account), tlv("52", "8099"),
        tlv("53", "840"), tlv("54", f"{amount:.2f}"), tlv("58", "US"),
        tlv("59", merchant), tlv("60", "LOS ANGELES"), tlv("62", extra), "6304",
    ])
    return base + f"{crc16(base.encode()):04X}"


def _money(value: str | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def inspect_qr(payload: str, expected_provider: str, expected_amount: float,
               expected_currency: str = "840", expected_invoice: str = "") -> dict:
    reasons: list[str] = []
    try:
        fields = parse_tlv(payload.strip())
    except ValueError as exc:
        return {"trusted": False, "reasons": [str(exc)], "mode": QR_MODE}
    crc_field = fields.get("63", "")
    prefix = payload.strip()[:-4]
    if len(crc_field) != 4 or f"{crc16(prefix.encode()):04X}" != crc_field.upper():
        reasons.append("QR checksum does not match")
    payment_networks = []
    for tag in range(26, 52):
        raw = fields.get(str(tag), "")
        if raw:
            try:
                payment_networks.append(parse_tlv(raw).get("00", ""))
            except ValueError:
                reasons.append("merchant account data is malformed")
    if not any(value.upper() == "VISA" for value in payment_networks):
        reasons.append("QR does not identify a Visa payment network")
    merchant = fields.get("59", "").strip()
    want = re.sub(r"[^A-Z0-9]", "", expected_provider.upper())
    got = re.sub(r"[^A-Z0-9]", "", merchant.upper())
    if want and want not in got and got not in want:
        reasons.append("merchant name does not match the care provider")
    try:
        amount = _money(fields.get("54", ""))
        if amount != _money(expected_amount):
            reasons.append("QR amount does not match the reviewed bill")
    except InvalidOperation:
        amount = Decimal("0")
        reasons.append("QR amount is missing or invalid")
    if fields.get("53") != expected_currency:
        reasons.append("QR currency is not the expected currency")
    invoice = ""
    if fields.get("62"):
        try:
            invoice = parse_tlv(fields["62"]).get("01", "")
        except ValueError:
            reasons.append("invoice reference is malformed")
    if expected_invoice and invoice != expected_invoice:
        reasons.append("QR invoice reference does not match")
    return {
        "trusted": not reasons, "reasons": reasons, "merchant_name": merchant,
        "amount": float(amount), "currency": fields.get("53", ""), "invoice": invoice,
        "mode": QR_MODE,
    }


def decode_qr_image(data: bytes) -> str:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ValueError("QR image decoding needs opencv-python-headless") from exc
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("could not read the QR image")
    value, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    if not value:
        raise ValueError("no readable QR code found")
    return value


def save_review(case_id: str, inspection: dict, payload: str) -> dict:
    review_id = "qrv_" + hashlib.sha256(f"{case_id}|{payload}".encode()).hexdigest()[:16]
    record = {**inspection, "settlement_id": review_id, "case_id": case_id,
              "direction": "clinic_payment", "status": "verified" if inspection["trusted"] else "rejected"}
    store.save_settlement(review_id, record)
    return record


def approve_qr(case_id: str, review_id: str) -> dict:
    record = store.get_settlement(review_id)
    if not record or record.get("case_id") != case_id:
        raise ValueError("QR review was not found for this case")
    if not record.get("trusted"):
        raise ValueError("an untrusted QR cannot be approved")
    if QR_MODE not in {"mock", "simulate"}:
        raise NotImplementedError("live Visa wallet handoff requires approved Visa Pay wallet integration")
    record.update(status="handoff_ready", handoff_url=f"{PUBLIC}/visa/qr/{review_id}")
    store.save_settlement(review_id, record)
    return record


def reimburse(case_id: str, benefit_name: str, amount: float, benefit_approved: bool) -> dict:
    if not benefit_approved or not benefit_name.strip():
        raise ValueError("verified benefit approval is required before reimbursement")
    if _money(amount) <= 0:
        raise ValueError("reimbursement amount must be positive")
    payout_id = "vdp_" + hashlib.sha256(f"{case_id}|{benefit_name}|{_money(amount)}".encode()).hexdigest()[:16]
    existing = store.get_settlement(payout_id)
    if existing:
        return existing
    if DIRECT_MODE not in {"mock", "simulate"}:
        raise NotImplementedError("live Visa Direct payout requires sponsor/acquirer onboarding and certified payout fields")
    record = {
        "settlement_id": payout_id, "case_id": case_id, "direction": "patient_reimbursement",
        "rail": "visa_direct", "amount": float(_money(amount)), "currency": "USD",
        "benefit_name": benefit_name.strip(), "benefit_approved": True,
        "status": "simulated_paid", "mode": DIRECT_MODE,
    }
    store.save_settlement(payout_id, record)
    return record


def safe_text(value: object) -> str:
    """Escape settlement values before placing them in the demo HTML handoff."""
    return html.escape(str(value), quote=True)
