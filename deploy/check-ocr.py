"""Live Core OCR smoke test using only the committed synthetic bill fixture.

Run inside the Core container with its normal environment. Prints safe counts,
never credentials, document text, file references, or real patient data.
"""
import io
import os
import sys
from pathlib import Path

import httpx
from PIL import Image


def main():
    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/backend/ocr/fixtures/synthetic_bill.png")
    image = fixture.read_bytes()
    output = io.BytesIO()
    with Image.open(io.BytesIO(image)) as document:
        document.convert("RGB").save(output, format="PDF")
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=90, trust_env=False,
                      headers={"x-internal-token": os.environ["INTERNAL_TOKEN"]}) as client:
        for kind, data, mime in (("photo", image, "application/octet-stream"),
                                 ("pdf", output.getvalue(), "application/pdf")):
            uploaded = client.post("/files", content=data, headers={"content-type": mime})
            assert uploaded.status_code == 200, f"{kind}: upload failed ({uploaded.status_code})"
            response = client.post("/reader/extract", json={"case_id": "ocr-synthetic-smoke", **uploaded.json()})
            assert response.status_code == 200, f"{kind}: reader failed ({response.status_code})"
            bill = response.json()
            assert bill["reader"] == "ocr", f"{kind}: synthetic fixture should not require a model call"
            assert len(bill["lines"]) == 5 and len(bill["unreviewed_lines"]) == 1
            assert abs(sum(line["charge"] for line in bill["lines"]) - 2807.75) < .01
            assert bill["needs_review"], f"{kind}: uncoded charges must need review"
            print(f"PASS {kind}: local OCR, 5 charges retained, review flag present")
        invalid = client.post("/files", content=b"not a receipt", headers={"content-type": "image/png"})
        assert invalid.status_code == 415
        missing = client.post("/reader/extract", json={"case_id": "ocr-synthetic-smoke"})
        assert missing.status_code == 422
        print("PASS guards: unsupported bytes rejected; missing document is not a demo")


if __name__ == "__main__":
    main()
