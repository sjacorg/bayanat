"""Extract plain text from DOCX files using docx2python."""

import re
from io import BytesIO

from docx2python import docx2python
from enferno.utils.logging_utils import get_logger

logger = get_logger()

# docx2python embeds image refs like: ----Image alt text---->...<----media/image1.png----
_IMAGE_REF_RE = re.compile(r"----.*?----")


def extract_docx_text(file_bytes: bytes) -> dict | None:
    try:
        with docx2python(BytesIO(file_bytes)) as doc:
            text = doc.text
        text = _IMAGE_REF_RE.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        words = text.split()
        return {
            "text": text,
            "word_count": len(words),
            "confidence": 100.0,
            "language": None,
            "orientation": 0,
            "raw": {},
        }
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return None
