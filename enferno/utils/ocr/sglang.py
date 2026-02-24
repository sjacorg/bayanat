"""SGLang/OpenAI-compatible OCR provider for self-hosted vision models."""

import base64
import re

import httpx
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from enferno.utils.logging_utils import get_logger

logger = get_logger()

SGLANG_DEFAULT_CONFIDENCE = 80.0


class SGLangError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=30),
    retry=retry_if_exception_type(SGLangError),
)
def extract_text(file_bytes: bytes, language_hints: list) -> dict | None:
    """Extract text via SGLang/OpenAI-compatible vision model."""
    try:
        base_url = current_app.config.get("SGLANG_OCR_URL", "http://localhost:8000")
        model = current_app.config.get("SGLANG_OCR_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")

        img_b64 = base64.b64encode(file_bytes).decode("utf-8")

        lang_str = ", ".join(language_hints) if language_hints else "Arabic, English"
        prompt = f"OCR this document. Extract all text exactly as written. Languages: {lang_str}"

        response = httpx.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.1,
            },
            timeout=300.0,
        )

        if response.status_code in (429, 500, 503, 524):
            raise SGLangError(f"SGLang returned {response.status_code}")

        response.raise_for_status()
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

        text = re.sub(r"^```\w*\n?|```$", "", text, flags=re.MULTILINE).strip()

        return {
            "text": text,
            "confidence": SGLANG_DEFAULT_CONFIDENCE,
            "word_count": len(text.split()),
            "language": None,
            "orientation": 0,
            "raw": data,
        }

    except SGLangError:
        raise

    except Exception as e:
        logger.error(f"SGLang OCR failed: {e}")
        return None
