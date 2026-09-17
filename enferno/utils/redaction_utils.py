import io
import threading
from contextlib import contextmanager

import pymupdf
from PIL import Image, ImageDraw, ImageFile, ImageOps

# Held across the decode, not just the flag flip: the flag is what the decode reads.
_TRUNCATED_LOCK = threading.Lock()


@contextmanager
def _allow_truncated_images():
    """Accept a truncated scan for the duration of one redaction decode.

    Field-captured photos regularly arrive with the upload cut short at the source.
    Browsers render whatever decoded, so the redaction UI shows the image and the user
    draws boxes on it; PIL alone refuses the same bytes with "broken data stream". Decode
    what is there so the burn covers exactly the pixels the user saw.

    Pillow reads this flag at decode time and it is process-global, so it is set around
    the one decode that needs it rather than at import, where it would also let every
    other consumer in the process (OCR, thumbnails, imports) silently accept incomplete
    images. The lock is what keeps that scoping true: the workers are threaded, and two
    overlapping redactions restoring each other's saved value can otherwise leave the
    flag on for the life of the process.
    """
    with _TRUNCATED_LOCK:
        previous = ImageFile.LOAD_TRUNCATED_IMAGES
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        try:
            yield
        finally:
            ImageFile.LOAD_TRUNCATED_IMAGES = previous


class RedactionError(ValueError):
    pass


def _validate_rect(rect: dict) -> None:
    required = {"x", "y", "w", "h"}
    if set(rect) != required:
        raise RedactionError("Redaction rectangle must contain x, y, w, and h")

    x = rect["x"]
    y = rect["y"]
    w = rect["w"]
    h = rect["h"]
    if not all(isinstance(value, int | float) for value in (x, y, w, h)):
        raise RedactionError("Redaction coordinates must be numeric")
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1 or y + h > 1:
        raise RedactionError("Redaction coordinates must be normalized within the page")


def _absolute_rect(rect: dict, width: float, height: float) -> pymupdf.Rect:
    _validate_rect(rect)
    return pymupdf.Rect(
        rect["x"] * width,
        rect["y"] * height,
        (rect["x"] + rect["w"]) * width,
        (rect["y"] + rect["h"]) * height,
    )


def _page_specs_by_index(doc: pymupdf.Document, pages: list[dict]) -> dict[int, list[dict]]:
    specs = {}
    for spec in pages:
        page_index = spec.get("page")
        if not isinstance(page_index, int) or page_index < 0 or page_index >= doc.page_count:
            raise RedactionError("Redaction page index is invalid")
        rects = spec.get("rects", [])
        if not isinstance(rects, list) or not rects:
            raise RedactionError("Redaction page must contain at least one rectangle")
        specs.setdefault(page_index, []).extend(rects)
    if not specs:
        raise RedactionError("No redaction regions provided")
    return specs


def redact_pdf_bytes(src: bytes, pages: list[dict]) -> bytes:
    doc = pymupdf.open(stream=src, filetype="pdf")
    try:
        for page_index, rects in _page_specs_by_index(doc, pages).items():
            page = doc[page_index]
            for rect in rects:
                page.add_redact_annot(
                    _absolute_rect(rect, page.rect.width, page.rect.height),
                    fill=(0, 0, 0),
                )
            page.apply_redactions()

        doc.scrub()
        return doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()


def rotate_rect_to_original(rect: dict, orientation: int) -> dict:
    """Map a normalized rect drawn on a rotated image back to the original image's coordinate space."""
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    if orientation == 90:
        return {"x": y, "y": 1 - x - w, "w": h, "h": w}
    if orientation == 180:
        return {"x": 1 - x - w, "y": 1 - y - h, "w": w, "h": h}
    if orientation == 270:
        return {"x": 1 - y - h, "y": x, "w": h, "h": w}
    return rect


def redact_image_bytes(src: bytes, rects: list[dict]) -> bytes:
    if not rects:
        raise RedactionError("No redaction regions provided")

    # Bake in EXIF orientation so we draw on the same pixels the browser displayed
    # (browsers honor EXIF; PIL does not). Otherwise boxes land in the wrong place and
    # the saved copy comes back at 0deg. The DB orientation axis is handled separately
    # by rotate_rect_to_original in the caller.
    try:
        with _allow_truncated_images():
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(src))).convert("RGB")
    except OSError as e:
        raise RedactionError("This image file is damaged and cannot be redacted") from e
    draw = ImageDraw.Draw(img)
    width, height = img.size
    for rect in rects:
        box = _absolute_rect(rect, width, height)
        draw.rectangle([box.x0, box.y0, box.x1, box.y1], fill=(0, 0, 0))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


def pdf_page_images(src: bytes, dpi: int = 110, max_pages: int = 20) -> list[bytes]:
    """Rasterize a PDF's pages to PNG bytes, capped at ``max_pages``."""
    doc = pymupdf.open(stream=src, filetype="pdf")
    try:
        return [page.get_pixmap(dpi=dpi).tobytes("png") for page in list(doc)[:max_pages]]
    finally:
        doc.close()
