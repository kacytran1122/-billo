"""Core compatibility wrapper for the OCR-first bill reader."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ocr.reader import PROMPT, demo_bill, read_bill  # noqa: E402,F401
