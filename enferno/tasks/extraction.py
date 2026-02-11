"""Background text extraction task using Google Vision OCR."""

import base64
import re
import unicodedata
from pathlib import Path

import httpx
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from enferno.admin.models import Media, Extraction
from enferno.extensions import db
from enferno.utils.logging_utils import get_logger
from enferno.utils.text_utils import normalize_arabic

logger = get_logger()

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"
DEFAULT_LANGUAGE_HINTS = ["ar", "en"]


def _get_api_key() -> str:
    """Get Google Vision API key from config."""
    key = current_app.config.get("GOOGLE_VISION_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_VISION_API_KEY not configured")
    return key


def _is_ocr_supported(media: Media) -> bool:
    """Check if media file extension is supported for OCR."""
    if not media.media_file:
        return False
    ext = Path(media.media_file).suffix.lstrip(".").lower()
    allowed = current_app.config.get("OCR_EXT", [])
    return ext in allowed


def process_media_extraction_task(media_id: int, language_hints: list = None) -> dict:
    """Extract text from a media file using Google Vision OCR."""
    try:
        media = Media.query.get(media_id)
        if not media:
            return {"success": False, "media_id": media_id, "error": "Media not found"}

        if media.extraction:
            if media.extraction.status == "failed":
                db.session.delete(media.extraction)
                db.session.commit()
            else:
                return {"success": True, "media_id": media_id, "skipped": True}

        if not _is_ocr_supported(media):
            return {"success": False, "media_id": media_id, "error": "Unsupported file type"}

        file_path = _get_media_path(media)
        if not file_path or not file_path.exists():
            return {"success": False, "media_id": media_id, "error": "File not found"}

        # Detect orientation (Tesseract OSD, fallback to 0)
        orientation = _detect_orientation(file_path)

        # OCR via Google Vision
        hints = language_hints or DEFAULT_LANGUAGE_HINTS
        result = _extract_text(file_path, hints)
        if result is None:
            _save_failed_extraction(media_id, "Vision API failed")
            return {"success": False, "media_id": media_id, "error": "Vision API failed"}

        confidence = result["confidence"]
        status = _route_by_confidence(confidence)

        # Save
        cleaned_text = _normalize(result["text"])
        extraction = Extraction(
            media_id=media_id,
            text=normalize_arabic(cleaned_text),
            original_text=cleaned_text,
            raw=result["raw"],
            confidence=confidence,
            orientation=orientation,
            status=status,
            word_count=result["word_count"],
            language=result["language"],
        )
        db.session.add(extraction)
        db.session.commit()

        logger.info(
            f"Extraction {media_id}: {confidence:.0f}% ({result['word_count']} words, {result['language']}) -> {status}"
        )

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
def _extract_text(file_path: Path, language_hints: list) -> dict | None:
    """Call Google Vision REST API with retry on errors.

    Returns dict with: text, confidence, word_count, language, raw (or None on failure).
    """
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
            return None

        # Parse response
        result = data.get("responses", [{}])[0]
        if "error" in result:
            logger.error(f"Vision API error: {result['error']}")
            return None

        annotation = result.get("fullTextAnnotation", {})
        text = annotation.get("text", "")

        if not text:
            return {"text": "", "confidence": 0.0, "word_count": 0, "language": None, "raw": data}

        # Extract metadata directly from Google's response
        page = annotation.get("pages", [{}])[0]
        confidence = page.get("confidence", 0.0) * 100  # Convert to 0-100 scale

        # Count words
        word_count = sum(
            1
            for blk in page.get("blocks", [])
            for para in blk.get("paragraphs", [])
            for _ in para.get("words", [])
        )

        # Get primary detected language
        languages = page.get("property", {}).get("detectedLanguages", [])
        language = languages[0].get("languageCode") if languages else None

        return {
            "text": text,
            "confidence": confidence,
            "word_count": word_count,
            "language": language,
            "raw": data,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Vision API HTTP error: {e}")
        return None

    except VisionAPIError:
        raise  # Let tenacity handle retry

    except Exception as e:
        logger.error(f"Vision API failed: {e}")
        return None


def _normalize(text: str) -> str:
    """Normalize text for storage and search while preserving line breaks."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    # Collapse horizontal whitespace (spaces, tabs) but preserve newlines
    text = re.sub(r"[^\S\n]+", " ", text)
    # Fix hyphenated words with spaces
    text = re.sub(r"-\s+", "-", text)
    # Clean up trailing spaces on lines
    text = re.sub(r" +\n", "\n", text)
    # Collapse 3+ newlines to double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _route_by_confidence(confidence: float) -> str:
    """Route extraction by confidence: >=85 processed, 70-84 review, <70 transcribe."""
    if confidence >= 85.0:
        return "processed"
    if confidence >= 70.0:
        return "needs_review"
    return "needs_transcription"


def _save_failed_extraction(media_id: int, error: str, raw: dict = None) -> None:
    """Save a failed extraction record so item doesn't stay in pending."""
    try:
        extraction = Extraction(
            media_id=media_id,
            text=None,
            raw=raw or {"error": error},
            confidence=0.0,
            status="failed",
        )
        db.session.add(extraction)
        db.session.commit()
        logger.info(f"Extraction {media_id}: marked as failed - {error}")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Failed to save failed extraction for {media_id}: {e}")
