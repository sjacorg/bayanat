"""PDF-to-images conversion for OCR pre-processing."""

import fitz  # PyMuPDF
from enferno.utils.logging_utils import get_logger

logger = get_logger()

DPI = 200
MAX_DIMENSION = 4096  # Cap longest side to keep Vision API happy


def pdf_to_images(file_bytes: bytes) -> list[bytes]:
    """Render each PDF page as a JPEG image.

    Returns a list of JPEG bytes, one per page. Empty list on failure.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        result = []
        for page in doc:
            pix = page.get_pixmap(dpi=DPI)
            longest = max(pix.width, pix.height)
            if longest > MAX_DIMENSION:
                scale = MAX_DIMENSION / longest
                pix = page.get_pixmap(matrix=fitz.Matrix(scale * DPI / 72, scale * DPI / 72))
            result.append(pix.tobytes("jpeg"))
        doc.close()
        logger.info(f"PDF split into {len(result)} page(s)")
        return result
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        return []
