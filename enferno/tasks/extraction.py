"""Background text extraction task using Google Vision OCR."""

import re
import unicodedata
from pathlib import Path

from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from google.cloud import vision
from google.protobuf.json_format import MessageToDict
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from enferno.admin.models import Media
from enferno.extensions import db
from enferno.utils.logging_utils import get_logger

logger = get_logger()

# Default language hints (Arabic primary)
DEFAULT_LANGUAGE_HINTS = ["ar", "en"]


def process_media_extraction_task(media_id: int, language_hints: list = None) -> dict:
    """Extract text from a media file using Google Vision OCR."""
    try:
        media = Media.query.get(media_id)
        if not media:
            return {"success": False, "media_id": media_id, "error": "Media not found"}

        if media.extraction:
            return {"success": True, "media_id": media_id, "skipped": True}

        file_path = _get_media_path(media)
        if not file_path or not file_path.exists():
            return {"success": False, "media_id": media_id, "error": "File not found"}

        # Detect orientation (Tesseract OSD, fallback to 0)
        orientation = _detect_orientation(file_path)

        # OCR via Google Vision
        hints = language_hints or DEFAULT_LANGUAGE_HINTS
        text, confidence, raw = _extract_text(file_path, hints)
        if text is None:
            return {"success": False, "media_id": media_id, "error": "Vision API failed"}

        # Route by confidence
        status = _route_by_confidence(confidence)

        # Save
        from enferno.admin.models import Extraction

        extraction = Extraction(
            media_id=media_id,
            text=_normalize(text),
            raw=raw,
            confidence=confidence,
            orientation=orientation,
            status=status,
        )
        db.session.add(extraction)
        db.session.commit()

        logger.info(f"Extraction {media_id}: {confidence:.0f}% -> {status}")

        return {
            "success": True,
            "media_id": media_id,
            "confidence": confidence,
            "status": status,
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"DB error for media {media_id}: {e}")
        return {"success": False, "media_id": media_id, "error": str(e)}

    except Exception as e:
        logger.error(f"Error processing media {media_id}: {e}")
        return {"success": False, "media_id": media_id, "error": str(e)}


def _get_media_path(media: Media) -> Path | None:
    """Get file path for media object."""
    if not media.media_file:
        return None
    return Media.media_dir / media.media_file


def _detect_orientation(file_path: Path) -> int:
    """Detect image orientation using Tesseract OSD. Returns 0 on failure."""
    try:
        import pytesseract
        from PIL import Image

        osd = pytesseract.image_to_osd(Image.open(file_path))
        for line in osd.split("\n"):
            if "Orientation in degrees" in line:
                return int(line.split(":")[1].strip())
        return 0
    except Exception as e:
        logger.warning(f"Orientation detection failed: {e}")
        return 0


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=30),
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    before_sleep=lambda retry_state: logger.warning(
        f"Vision API rate limited, retry {retry_state.attempt_number}/3"
    ),
)
def _extract_text(file_path: Path, language_hints: list) -> tuple[str | None, float, dict | None]:
    """Call Google Vision API with retry on rate limits."""
    try:
        client = vision.ImageAnnotatorClient()

        with open(file_path, "rb") as f:
            image = vision.Image(content=f.read())

        # Language hints improve accuracy for Arabic
        image_context = vision.ImageContext(language_hints=language_hints)
        response = client.document_text_detection(image=image, image_context=image_context)

        if response.error.message:
            logger.error(f"Vision API error: {response.error.message}")
            return None, 0.0, None

        # Store raw response
        raw = MessageToDict(response._pb)

        annotation = response.full_text_annotation
        if not annotation or not annotation.text:
            return "", 0.0, raw

        text = annotation.text
        confidence = _calculate_confidence(annotation)

        return text, confidence, raw

    except (ResourceExhausted, ServiceUnavailable):
        raise  # Let tenacity handle retry

    except Exception as e:
        logger.error(f"Vision API failed: {e}")
        return None, 0.0, None


def _calculate_confidence(annotation) -> float:
    """Calculate average word-level confidence (0-100 scale)."""
    confidences = []
    for page in annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    if word.confidence:
                        confidences.append(word.confidence)

    if not confidences:
        return 0.0

    return sum(confidences) / len(confidences) * 100


def _normalize(text: str) -> str:
    """Normalize text for storage and search."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "-", text)
    return text.strip()


def _route_by_confidence(confidence: float) -> str:
    """Route extraction by confidence: >=85 processed, 70-84 review, <70 transcribe."""
    if confidence >= 85.0:
        return "processed"
    if confidence >= 70.0:
        return "needs_review"
    return "needs_transcription"
