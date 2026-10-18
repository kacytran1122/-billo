"""Billo bill reader: OCR first, ChatGPT vision as the fallback.

Same call and same output shape as backend/api/app/reader.py `read_bill`, so it is a
drop-in replacement. Each result also says which reader produced it:

    reader = "ocr"            OCR read the bill and the lines add up
    reader = "vision"         OCR could not, ChatGPT read it; each line is
                              checked against the OCR text (`verified`)
    reader = "demo"           demo=True, or no file
    reader = "demo_fallback"  nothing could read the photo and there is no
                              vision key (same behaviour as the old reader)

The AI only reads. Code makes every decision.
"""
from __future__ import annotations

import base64
import contextlib
import json
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from . import engine
from .parse import parse_bill
from .verify import verify_lines

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]


def _repo_path(env_name: str, default: Path) -> Path:
    configured = os.getenv(env_name, "").strip()
    if not configured:
        return default
    path = Path(configured)
    return path if path.is_absolute() else REPO_ROOT / path


UPLOADS = _repo_path("BILLO_UPLOADS_DIR", BACKEND_ROOT / "api" / "uploads")
DEMO_BILL = _repo_path("BILLO_DEMO_BILL", BACKEND_ROOT / "data" / "synthetic" / "maya_bill.json")
MAX_IMAGE_BYTES = int(os.getenv("OCR_MAX_IMAGE_BYTES", str(20 * 1024 * 1024)))

MIN_CONF = float(os.getenv("OCR_MIN_CONFIDENCE", "0.6"))
MIN_LINES = int(os.getenv("OCR_MIN_LINES", "1"))

PROMPT = (
    "You read itemized medical bills. Return ONLY JSON: "
    '{"hospital_npi": "<10 digits or empty>", "lines": [{"line_no": 1, "code": "<CPT/HCPCS>", '
    '"description": "...", "units": 1, "charge": 0.0, "service_date": "YYYY-MM-DD"}]}. '
    "Copy numbers exactly. If a field is unreadable, use an empty string. Do not guess codes."
)


def _span(op: str, name: str):
    try:
        import sentry_sdk

        return sentry_sdk.start_span(op=op, name=name)
    except Exception:
        return contextlib.nullcontext()


def demo_bill(reader: str = "demo") -> dict:
    bill = json.loads(DEMO_BILL.read_text())
    bill["reader"] = reader
    return bill


def load_image(file_url: str) -> tuple[bytes, str]:
    """Return (bytes, mime) for file:, data: or http(s) URLs."""
    if file_url.startswith("file:"):  # uploaded through the iMessage bridge
        path = UPLOADS / Path(file_url[5:]).name  # .name blocks ../ tricks
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "heic": "image/heic"}.get(path.suffix[1:].lower(), "image/jpeg")
        data = path.read_bytes()
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("bill image is too large")
        return data, mime
    if file_url.startswith("data:"):
        head, data = file_url.split(",", 1)
        decoded = base64.b64decode(data, validate=True)
        if len(decoded) > MAX_IMAGE_BYTES:
            raise ValueError("bill image is too large")
        return decoded, head[5:].split(";")[0] or "image/jpeg"
    if urlparse(file_url).scheme not in {"http", "https"}:
        raise ValueError("bill image URL must use file, data, http, or https")
    req = urllib.request.Request(file_url, headers={"User-Agent": "Billo/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        content_length = int(r.headers.get("Content-Length") or 0)
        if content_length > MAX_IMAGE_BYTES:
            raise ValueError("bill image is too large")
        data = r.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("bill image is too large")
        return data, r.headers.get_content_type() or "image/jpeg"


def _valid(bill: dict) -> dict:
    """Clean the vision model's JSON exactly like the original reader did."""
    lines = []
    for i, l in enumerate(bill.get("lines", []), 1):
        charge = float(str(l.get("charge", 0)).replace("$", "").replace(",", "") or 0)
        if charge <= 0 or not str(l.get("code", "")).strip():
            continue
        lines.append({"line_no": int(l.get("line_no") or i), "code": str(l["code"]).strip(),
                      "description": str(l.get("description", ""))[:120],
                      "units": int(l.get("units") or 1),
                      "charge": round(charge, 2), "service_date": str(l.get("service_date", ""))})
    if not lines:
        raise ValueError("bill reader returned no valid lines")
    return {"hospital_npi": str(bill.get("hospital_npi", "")), "lines": lines}


def _vision(image: bytes, mime: str, strict: bool) -> dict:
    from openai import OpenAI

    client = OpenAI(base_url=os.getenv("VISION_BASE_URL", "https://api.openai.com/v1"),
                    api_key=os.getenv("VISION_API_KEY", "").strip())
    url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    resp = client.chat.completions.create(
        model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": PROMPT + (" Be extra strict: skip any line you cannot read fully." if strict else "")},
            {"role": "user", "content": [{"type": "text", "text": "Read this bill."},
                                         {"type": "image_url", "image_url": {"url": url}}]},
        ],
    )
    return _valid(json.loads(resp.choices[0].message.content or "{}"))


def ocr_usable(parsed: dict, strict: bool = False) -> tuple[bool, str]:
    """Decide whether the OCR result is good enough to skip the vision model."""
    lines = parsed["lines"]
    if len(lines) < MIN_LINES:
        return False, "too few coded lines"
    min_conf = MIN_CONF + (0.15 if strict else 0)
    if sum(l["confidence"] for l in lines) / len(lines) < min_conf:
        return False, "low OCR confidence"
    if parsed["totals_match"] is False:
        return False, "lines do not add up to the printed total"
    return True, "ok"


def read_bill(file_url: str, demo: bool, strict: bool = False) -> dict:
    if demo or not file_url:
        return demo_bill()

    image, mime = load_image(file_url)

    with _span("ocr", "ocr bill"):
        boxes = engine.run_ocr(image)

    ocr_reason = "OCR not installed"
    if boxes:
        parsed = parse_bill(boxes)
        ok, ocr_reason = ocr_usable(parsed, strict)
        if ok:
            for l in parsed["lines"]:
                l["source"], l["verified"] = "ocr", True
            return {"reader": "ocr", **parsed}

    if os.getenv("VISION_API_KEY", "").strip():
        with _span("gen_ai.vision", "read bill (vision fallback)"):
            bill = _vision(image, mime, strict)
        for l in bill["lines"]:
            l["source"] = "vision"
        verify_lines(bill["lines"], boxes)
        bill["reader"] = "vision"
        bill["fallback_reason"] = ocr_reason
        bill["needs_review"] = [l["line_no"] for l in bill["lines"] if l["verified"] is False]
        return bill

    if os.getenv("BILLO_MODE", "demo") == "demo":
        return demo_bill("demo_fallback") | {"fallback_reason": ocr_reason}

    raise ValueError(
        f"The bill could not be read reliably ({ocr_reason}). "
        "Upload a clearer image or configure VISION_API_KEY for the fallback reader."
    )
