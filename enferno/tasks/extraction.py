"""Background text extraction task using configurable OCR provider."""

import re
import unicodedata
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from enferno.admin.models import Extraction, Media
from enferno.extensions import db
from enferno.utils.logging_utils import get_logger
from enferno.utils.ocr import get_provider

logger = get_logger()

DEFAULT_LANGUAGE_HINTS = ["ar", "en"]


def _is_ocr_supported(media: Media) -> bool:
    """Check if media file extension is supported for OCR."""
    if not media.media_file:
        return False
    ext = Path(media.media_file).suffix.lstrip(".").lower()
    allowed = current_app.config.get("OCR_EXT", [])
    return ext in allowed


def process_media_extraction_task(
    media_id: int, language_hints: list = None, force: bool = False
) -> dict:
    """Extract text from a media file using the configured OCR provider."""
    try:
        media = Media.query.get(media_id)
        if not media:
            return {"success": False, "media_id": media_id, "error": "Media not found"}

        if media.extraction:
            if force or media.extraction.status == "failed":
                db.session.delete(media.extraction)
                db.session.commit()
            else:
                return {"success": True, "media_id": media_id, "skipped": True}

        if not _is_ocr_supported(media):
            return {"success": False, "media_id": media_id, "error": "Unsupported file type"}

        file_bytes = _read_media_bytes(media)
        if not file_bytes:
            return {"success": False, "media_id": media_id, "error": "File not found"}

        provider_name = current_app.config.get("OCR_PROVIDER", "google_vision")
        extract_text = get_provider(provider_name)
        hints = language_hints or DEFAULT_LANGUAGE_HINTS
        result = extract_text(file_bytes, hints)

        if result is None:
            _save_failed_extraction(media_id, f"{provider_name} failed")
            return {"success": False, "media_id": media_id, "error": f"{provider_name} failed"}

        confidence = result["confidence"]
        status = "processed"

        cleaned_text = _normalize(result["text"])
        detected_orientation = result.get("orientation", 0)
        extraction = Extraction(
            media_id=media_id,
            text=cleaned_text,
            original_text=cleaned_text,
            raw=result["raw"],
            confidence=confidence,
            orientation=detected_orientation,
            status=status,
            word_count=result["word_count"],
            language=result["language"],
        )
        db.session.add(extraction)
        if detected_orientation:
            media.orientation = detected_orientation
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


def _read_media_bytes(media: Media) -> bytes | None:
    """Read media file bytes from local filesystem or S3."""
    if not media.media_file:
        return None

    if current_app.config.get("FILESYSTEM_LOCAL"):
        path = Media.media_dir / media.media_file
        if not path.exists():
            return None
        return path.read_bytes()

    try:
        s3 = boto3.client(
            "s3",
            config=BotoConfig(signature_version="s3v4"),
            aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
            region_name=current_app.config["AWS_REGION"],
        )
        response = s3.get_object(Bucket=current_app.config["S3_BUCKET"], Key=media.media_file)
        return response["Body"].read()
    except Exception as e:
        logger.error(f"S3 read failed for {media.media_file}: {e}")
        return None


def _normalize(text: str) -> str:
    """Normalize text for storage and search while preserving line breaks."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"-\s+", "-", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
