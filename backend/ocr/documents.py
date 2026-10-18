"""Bounded, in-memory decoding for bill photos and short PDF documents."""
from __future__ import annotations

import io
import math
import threading

MAX_PAGES = 4
MAX_PIXELS = 24_000_000
MAX_RENDER_SIDE = 2400
_PDF_LOCK = threading.Lock()  # PDFium must not be called concurrently in threads.


def content_type(data: bytes) -> str:
    """Use bytes, not a sender-controlled filename or MIME header."""
    if data.lstrip().startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[4:8] == b"ftyp" and any(brand in data[8:64] for brand in
                                   (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"heif", b"mif1", b"msf1")):
        return "image/heic"
    raise ValueError("Send a JPEG, PNG, WebP, HEIC photo or a PDF bill or receipt.")


def _png(image) -> bytes:
    from PIL import Image, ImageOps

    if image.width * image.height > MAX_PIXELS:
        raise ValueError("This photo is too large to decode safely. Send a smaller photo.")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((MAX_RENDER_SIDE, MAX_RENDER_SIDE), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def pages(data: bytes, mime: str) -> list[bytes]:
    """Return PNG pages; never silently truncate a multi-page bill."""
    if mime == "application/pdf":
        return _pdf_pages(data)
    from PIL import Image

    if mime == "image/heic":
        try:
            from pillow_heif import register_heif_opener

            register_heif_opener()
        except ImportError as exc:
            raise ValueError("HEIC decoding is unavailable. Send a JPEG or PNG photo.") from exc
    try:
        with Image.open(io.BytesIO(data)) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Send one still photo, not an animated or multi-frame image.")
            return [_png(image)]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("This photo could not be decoded. Send a clear JPEG or PNG photo.") from exc


def _pdf_pages(data: bytes) -> list[bytes]:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ValueError("PDF reading is unavailable. Send clear photos of the bill pages instead.") from exc
    try:
        with _PDF_LOCK, pdfium.PdfDocument(data) as document:
            if not 1 <= len(document) <= MAX_PAGES:
                raise ValueError(f"Send a PDF with 1 to {MAX_PAGES} pages, or split this document.")
            output = []
            for index in range(len(document)):
                page = document[index]
                try:
                    width, height = page.get_size()
                    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                        raise ValueError("This PDF has an invalid page size. Send a photo instead.")
                    bitmap = page.render(scale=min(2.5, MAX_RENDER_SIDE / max(width, height)))
                    try:
                        with bitmap.to_pil() as image:
                            output.append(_png(image))
                    finally:
                        bitmap.close()
                finally:
                    page.close()
            return output
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("This PDF could not be opened. Send an unlocked PDF or clear page photos.") from exc
