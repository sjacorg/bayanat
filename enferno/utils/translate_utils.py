"""Google Cloud Translation API (v2 Basic)."""

import httpx
from flask import current_app

from enferno.utils.logging_utils import get_logger

logger = get_logger()

TRANSLATE_API_URL = "https://translation.googleapis.com/language/translate/v2"


def translate_text(text: str, target_language: str = "fr", source_language: str = None) -> dict:
    """Translate text using Google Translate API.

    Returns dict with: translated_text, source_language, target_language.
    Raises RuntimeError on failure.
    """
    key = current_app.config.get("GOOGLE_VISION_API_KEY")
    if not key:
        raise RuntimeError("Google API key not configured")

    if not text or not text.strip():
        raise ValueError("No text to translate")

    params = {
        "key": key,
        "q": text,
        "target": target_language,
        "format": "text",
    }
    if source_language and source_language != target_language:
        params["source"] = source_language

    response = httpx.post(TRANSLATE_API_URL, data=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    translation = data["data"]["translations"][0]
    return {
        "translated_text": translation["translatedText"],
        "source_language": translation.get("detectedSourceLanguage", source_language),
        "target_language": target_language,
    }
