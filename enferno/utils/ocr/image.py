"""Shared image preprocessing for OCR providers."""

import io

from PIL import Image, ImageOps

from enferno.utils.logging_utils import get_logger

logger = get_logger()

MAX_DIMENSION = 4096


def prepare_image(file_bytes: bytes, max_dimension: int = MAX_DIMENSION) -> bytes:
    """Normalize image for OCR: fix EXIF orientation, cap dimensions, output JPEG."""
    img = Image.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)

    w, h = img.size
    longest = max(w, h)
    if longest > max_dimension:
        scale = max_dimension / longest
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        logger.info(f"OCR: downscaled {w}x{h} -> {new_w}x{new_h}")

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
