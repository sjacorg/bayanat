"""LLM OCR provider. Works with any OpenAI-compatible endpoint (Ollama, SGLang, vLLM, etc.)."""

import base64
import re

import httpx
from flask import current_app
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    RetryError,
)

from enferno.utils.logging_utils import get_logger
from enferno.utils.ocr.image import prepare_image

logger = get_logger()

DEFAULT_CONFIDENCE = 80.0
LLM_MAX_DIMENSION = 2048


class LLMProviderError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=30),
    retry=retry_if_exception_type(LLMProviderError),
)
def _extract_text_inner(file_bytes: bytes, language_hints: list) -> dict | None:
    """Extract text via any OpenAI-compatible vision model."""
    base_url = current_app.config.get("LLM_OCR_URL", "http://localhost:11434")
    model = current_app.config.get("LLM_OCR_MODEL", "llava")
    api_key = current_app.config.get("LLM_OCR_API_KEY")

    file_bytes = prepare_image(file_bytes, max_dimension=LLM_MAX_DIMENSION)
    img_b64 = base64.b64encode(file_bytes).decode("utf-8")

    lang_str = ", ".join(language_hints) if language_hints else "Arabic, English"

    system_msg = (
        "You are an OCR engine. Output ONLY the raw text from the image, nothing else. "
        "No introductions, no explanations, no commentary, no refusals. "
        "If the image contains no readable text, output an empty string."
    )
    prompt = f"Extract all text exactly as written. Languages: {lang_str}"

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = httpx.post(
            f"{base_url}/v1/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    },
                ],
                "max_tokens": 4096,
                "temperature": 0.0,
            },
            timeout=300.0,
        )
    except httpx.TransportError as e:
        logger.error(f"LLM OCR connection failed: {e}")
        return None

    if response.status_code in (429, 500, 503, 524):
        raise LLMProviderError(f"LLM provider returned {response.status_code}")

    if response.status_code >= 400:
        logger.error(f"LLM OCR error {response.status_code}: {response.text[:500]}")
        return None

    data = response.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
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

    # Strip LLM conversational preamble/refusals
    preamble = re.match(
        r"^(Sure[,.].*?:|Here is.*?:|I'm sorry.*?\.|I cannot.*?\.|I can't.*?\.)\s*",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if preamble:
        text = text[preamble.end() :].strip()

    return {
        "text": text,
        "confidence": DEFAULT_CONFIDENCE,
        "word_count": len(text.split()),
        "language": None,
        "orientation": 0,
        "raw": data,
    }


def extract_text(file_bytes: bytes, language_hints: list) -> dict | None:
    """Wrapper that catches retry exhaustion."""
    try:
        return _extract_text_inner(file_bytes, language_hints)
    except RetryError:
        logger.error("LLM OCR: all retry attempts failed")
        return None
