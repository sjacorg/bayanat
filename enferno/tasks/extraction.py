"""Background text extraction task using Google Vision OCR."""

import base64
import os
import re
import unicodedata
from pathlib import Path

import httpx
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from enferno.admin.models import Media
from enferno.extensions import db
from enferno.utils.logging_utils import get_logger

logger = get_logger()

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"
DEFAULT_LANGUAGE_HINTS = ["ar", "en"]


def _get_api_key() -> str:
    """Get Google Vision API key from environment."""
    key = os.environ.get("GOOGLE_VISION_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_VISION_API_KEY environment variable not set")
    return key


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


class VisionAPIError(Exception):
    """Raised when Vision API returns an error or rate limit."""

    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=30),
    retry=retry_if_exception_type(VisionAPIError),
    before_sleep=lambda retry_state: logger.warning(
        f"Vision API error, retry {retry_state.attempt_number}/3"
    ),
)
def _extract_text(file_path: Path, language_hints: list) -> tuple[str | None, float, dict | None]:
    """Call Google Vision REST API with retry on errors."""
    try:
        api_key = _get_api_key()

        with open(file_path, "rb") as f:
            image_content = base64.b64encode(f.read()).decode("utf-8")

        response = httpx.post(
            f"{VISION_API_URL}?key={api_key}",
            json={
                "requests": [
                    {
                        "image": {"content": image_content},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                        "imageContext": {"languageHints": language_hints},
                    }
                ]
            },
            timeout=60.0,
        )

        # Rate limit or server error - retry
        if response.status_code in (429, 500, 503):
            raise VisionAPIError(f"API returned {response.status_code}")

        response.raise_for_status()
        data = response.json()

        # Check for API error in response
        if "error" in data:
            logger.error(f"Vision API error: {data['error']}")
            return None, 0.0, None

        # Parse response
        result = data.get("responses", [{}])[0]
        if "error" in result:
            logger.error(f"Vision API error: {result['error']}")
            return None, 0.0, None

        annotation = result.get("fullTextAnnotation", {})
        text = annotation.get("text", "")

        if not text:
            return "", 0.0, data

        confidence = _calculate_confidence(annotation)
        return text, confidence, data

    except httpx.HTTPStatusError as e:
        logger.error(f"Vision API HTTP error: {e}")
        return None, 0.0, None

    except VisionAPIError:
        raise  # Let tenacity handle retry

    except Exception as e:
        logger.error(f"Vision API failed: {e}")
        return None, 0.0, None


def _calculate_confidence(annotation: dict) -> float:
    """Calculate average word-level confidence (0-100 scale)."""
    confidences = []
    for page in annotation.get("pages", []):
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    conf = word.get("confidence")
                    if conf is not None:
                        confidences.append(conf)

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
