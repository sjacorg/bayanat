"""Ollama OCR provider for self-hosted vision models."""

import base64
import re

import httpx
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from enferno.utils.logging_utils import get_logger

logger = get_logger()

# Ollama models don't return confidence scores.
# Default to needs_review tier so human review is always triggered.
OLLAMA_DEFAULT_CONFIDENCE = 80.0


class OllamaError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=30),
    retry=retry_if_exception_type(OllamaError),
)
def extract_text(file_bytes: bytes, language_hints: list) -> dict | None:
    """Extract text via Ollama vision model."""
    try:
        base_url = current_app.config.get("OLLAMA_OCR_URL", "http://localhost:11434")
        model = current_app.config.get("OLLAMA_OCR_MODEL", "deepseek-ocr")

        img_b64 = base64.b64encode(file_bytes).decode("utf-8")

        lang_str = ", ".join(language_hints) if language_hints else "Arabic, English"
        prompt = f"OCR this document. Extract all text exactly as written. Languages: {lang_str}"

        response = httpx.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [img_b64],
                    }
                ],
                "stream": False,
            },
            timeout=300.0,
        )

        if response.status_code in (429, 500, 503, 524):
            raise OllamaError(f"Ollama returned {response.status_code}")

        response.raise_for_status()
        data = response.json()

        text = data.get("message", {}).get("content", "").strip()
        if not text:
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "language": None,
                "orientation": 0,
                "raw": data,
            }

        # Strip markdown code fences if model wraps output
        text = re.sub(r"^```\w*\n?|```$", "", text, flags=re.MULTILINE).strip()

        return {
            "text": text,
            "confidence": OLLAMA_DEFAULT_CONFIDENCE,
            "word_count": len(text.split()),
            "language": None,
            "orientation": 0,
            "raw": data,
        }

    except OllamaError:
        raise

    except Exception as e:
        logger.error(f"Ollama OCR failed: {e}")
        return None
