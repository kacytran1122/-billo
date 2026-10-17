"""Document Reader: AI turns a bill photo into typed lines. It never decides anything.

demo=True (or no vision key) -> the synthetic Maya bill.
Otherwise -> an OpenAI-compatible vision model with a strict JSON answer,
then every line is validated; bad output is rejected (Sentry AI monitoring sees it).
"""
from __future__ import annotations

import json
import os

from .store import SYN

PROMPT = (
    "You read itemized medical bills. Return ONLY JSON: "
    '{"hospital_npi": "<10 digits or empty>", "lines": [{"line_no": 1, "code": "<CPT/HCPCS>", '
    '"description": "...", "units": 1, "charge": 0.0, "service_date": "YYYY-MM-DD"}]}. '
    "Copy numbers exactly. If a field is unreadable, use an empty string. Do not guess codes."
)


def demo_bill() -> dict:
    return json.loads((SYN / "maya_bill.json").read_text())


def _valid(bill: dict) -> dict:
    lines = []
    for i, l in enumerate(bill.get("lines", []), 1):
        charge = float(str(l.get("charge", 0)).replace("$", "").replace(",", "") or 0)
        if charge <= 0 or not str(l.get("code", "")).strip():
            continue
        lines.append({"line_no": int(l.get("line_no") or i), "code": str(l["code"]).strip(),
                      "description": str(l.get("description", ""))[:120], "units": int(l.get("units") or 1),
                      "charge": round(charge, 2), "service_date": str(l.get("service_date", ""))})
    if not lines:
        raise ValueError("bill reader returned no valid lines")
    return {"hospital_npi": str(bill.get("hospital_npi", "")), "lines": lines}


def read_bill(file_url: str, demo: bool, strict: bool = False) -> dict:
    key = os.getenv("VISION_API_KEY", "").strip()
    if demo or not file_url or not key:
        return demo_bill()
    from openai import OpenAI

    if file_url.startswith("file:"):  # uploaded through the iMessage bridge -> send as a data URL
        import base64
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "uploads" / Path(file_url[5:]).name  # no ../ tricks
        mime = {"jpg": "image/jpeg", "png": "image/png", "heic": "image/heic"}.get(path.suffix[1:], "image/jpeg")
        file_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"

    client = OpenAI(base_url=os.getenv("VISION_BASE_URL", "https://api.openai.com/v1"), api_key=key)
    resp = client.chat.completions.create(
        model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": PROMPT + (" Be extra strict: skip any line you cannot read fully." if strict else "")},
            {"role": "user", "content": [{"type": "text", "text": "Read this bill."},
                                         {"type": "image_url", "image_url": {"url": file_url}}]},
        ],
    )
    return _valid(json.loads(resp.choices[0].message.content or "{}"))
