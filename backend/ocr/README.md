# Billo OCR bill reader

Reads a bill photo with **OCR first**, and uses **ChatGPT vision as the fallback**.
When ChatGPT is used, every line it returns is **checked against what OCR saw on the photo**,
so a misread or invented number is flagged instead of trusted.

The AI only reads. Code makes every decision (same rule as the rest of Billo).

## How it decides

```
photo
  │
  ├─ demo=True or no file ─────────────────────────► Maya demo bill   reader="demo"
  │
  ├─ OCR (RapidOCR, local) ─► rows ─► lines
  │     usable if: ≥1 coded line, avg confidence ≥ 0.6,
  │     and the lines add up to the printed TOTAL (when the bill shows one)
  │     └─ usable ─────────────────────────────────► reader="ocr"
  │
  ├─ else ChatGPT vision (VISION_MODEL, default gpt-4o-mini)
  │     └─ each line cross-checked vs OCR text ────► reader="vision"
  │          line.verified = True / False / None (no OCR)
  │          needs_review = [line numbers that did not match]
  │
  └─ else (no OCR result and no VISION_API_KEY) ───► demo bill, reader="demo_fallback"
```

## What the output looks like

Same shape as the old reader (`hospital_npi`, `lines[]` with `line_no, code, description,
units, charge, service_date`), plus:

| Field | Meaning |
|---|---|
| `reader` | `ocr`, `vision`, `demo`, or `demo_fallback`. Show it in the UI/demo. |
| `lines[].source` | `ocr` or `vision` |
| `lines[].verified` | OCR lines: `True`. Vision lines: `True` if charge and code were seen on the photo, `False` if not, `None` if OCR was unavailable |
| `lines[].bbox` | `[x0, y0, x1, y1]` on the (upscaled) photo, for highlighting the source |
| `lines[].modifier`, `rev_code`, `confidence` | OCR only |
| `unreviewed_lines` | OCR rows with a charge but **no CPT/HCPCS code** (room, pharmacy, supplies). The old reader silently dropped these; ask the user about them. |
| `printed_total`, `parsed_total`, `totals_match` | OCR only. Sanity check that nothing was missed |
| `fallback_reason` | Why OCR was not used (e.g. "lines do not add up to the printed total") |
| `needs_review` | Vision only. Line numbers ChatGPT returned that OCR could not confirm |

If your rules engine (`backend/api/app/rules.py`) rejects unknown keys, strip the extra fields before
auditing. They are additive and safe to ignore.

## Integration

This package is wired into `backend/api/app/reader.py`; `/reader/extract` and the After-Care Organizer keep the
same interface. OCR dependencies are included in `backend/api/requirements.txt`, so the normal
`make setup` installs them. Run all project and OCR tests from the repo root:

```bash
make test
```

The real-OCR test runs on `tests/backend/ocr/fixtures/synthetic_bill.png`, a generated bill with no real
patient data, and is skipped if RapidOCR is not installed.

## Settings (optional, in `.env`)

| Variable | Default | |
|---|---|---|
| `OCR_MIN_CONFIDENCE` | `0.6` | Below this average OCR confidence, fall back to ChatGPT |
| `OCR_MIN_LINES` | `1` | Minimum coded lines for OCR to count as usable |
| `VISION_API_KEY`, `VISION_MODEL`, `VISION_BASE_URL` | unchanged | ChatGPT fallback, same as before |
| `BILLO_UPLOADS_DIR` | `backend/api/uploads` | Where iMessage uploads land (`file:` URLs) |
| `BILLO_DEMO_BILL` | `backend/data/synthetic/maya_bill.json` | Demo bill |

## Sentry

OCR runs inside a span `op="ocr"`; the fallback runs inside `op="gen_ai.vision"` (same op the
After-Care Organizer already uses). `fallback_reason` is a good tag for the Case Medic story.

## Known limits

- Tuned for printed, itemized bills with one charge per row. Handwritten or very skewed photos
  will usually fall back to ChatGPT, which is the point of the fallback.
- Local OCR accepts JPEG, PNG and HEIC images. Convert PDFs to an image before upload.
- Lone single-digit quantities are often missed by OCR; units are then worked out from
  unit price × units = total, which is more reliable anyway.
- First OCR call downloads/loads the ONNX models (~15 MB, a few seconds). Warm it up on startup
  if you want a fast first demo: `from ocr import engine; engine.available()`.
