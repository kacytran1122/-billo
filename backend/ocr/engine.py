"""OCR engine: image bytes -> text boxes with positions.

Uses RapidOCR (local, free, no API key). If the library is not installed,
`run_ocr` returns None and the reader falls back to the vision model.
"""
from __future__ import annotations

import io
import threading
from dataclasses import dataclass
from functools import lru_cache

_OCR_LOCK = threading.RLock()


@dataclass
class Box:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return max(1.0, self.y1 - self.y0)

    def bbox(self) -> list[int]:
        return [round(self.x0), round(self.y0), round(self.x1), round(self.y1)]


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR  # optional dependency

    # The production VM is small. Unbounded ONNX thread pools stall every agent.
    return RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)


def available() -> bool:
    try:
        _engine()
        return True
    except Exception:
        return False


def _to_array(image: bytes):
    """Decode JPEG/PNG (and HEIC if pillow-heif is installed) into an RGB numpy array."""
    import numpy as np
    from PIL import Image, ImageOps

    try:  # iPhone photos arrive as HEIC through iMessage
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except Exception:
        pass
    img = Image.open(io.BytesIO(image))
    img = ImageOps.exif_transpose(img).convert("RGB")  # respect phone rotation
    # Small photos read badly; upscale so text is at least ~20px tall.
    if max(img.size) < 1600:
        scale = 1600 / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)))
    return np.array(img)


def run_ocr(image: bytes) -> list[Box] | None:
    """Return text boxes, or None if OCR is unavailable or failed."""
    try:
        with _OCR_LOCK:
            engine = _engine()
    except Exception:
        return None
    try:
        with _OCR_LOCK:
            result, _ = engine(_to_array(image))
    except Exception:
        return None
    boxes: list[Box] = []
    for pts, text, conf in result or []:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        boxes.append(Box(str(text).strip(), min(xs), min(ys), max(xs), max(ys), float(conf)))
    return [b for b in boxes if b.text]
