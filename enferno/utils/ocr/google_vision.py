"""Google Vision OCR provider."""

import base64
import math
from collections import Counter

import httpx
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from enferno.utils.logging_utils import get_logger

logger = get_logger()

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"


class VisionAPIError(Exception):
    pass


def _get_api_key() -> str:
    key = current_app.config.get("GOOGLE_VISION_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_VISION_API_KEY not configured")
    return key


def _orientation_from_vision(page: dict) -> int:
    """Detect text orientation from Vision API block bounding boxes.

    Returns correction angle in degrees (0, 90, 180, 270).
    """
    blocks = page.get("blocks", [])
    if not blocks:
        return 0

    angles = []
    for block in blocks:
        if block.get("blockType") not in ("TEXT", None):
            continue
        vertices = block.get("boundingBox", {}).get("vertices", [])
        if len(vertices) < 2:
            continue
        dx = vertices[1].get("x", 0) - vertices[0].get("x", 0)
        dy = vertices[1].get("y", 0) - vertices[0].get("y", 0)
        angle = math.degrees(math.atan2(dy, dx))
        snapped = round(angle / 90) * 90
        angles.append(int(snapped % 360))

    if not angles:
        return 0

    text_direction = Counter(angles).most_common(1)[0][0]
    return (360 - text_direction) % 360


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=30),
    retry=retry_if_exception_type(VisionAPIError),
    before_sleep=lambda retry_state: logger.warning(
        f"Vision API error, retry {retry_state.attempt_number}/3"
    ),
)
def extract_text(file_bytes: bytes, language_hints: list) -> dict | None:
    """Call Google Vision REST API with retry.

    Returns dict with: text, confidence, word_count, language, orientation, raw.
    """
    try:
        api_key = _get_api_key()
        image_content = base64.b64encode(file_bytes).decode("utf-8")

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

        if response.status_code in (429, 500, 503):
            raise VisionAPIError(f"API returned {response.status_code}")

        response.raise_for_status()
        data = response.json()

        if "error" in data:
            logger.error(f"Vision API error: {data['error']}")
            return None

        result = data.get("responses", [{}])[0]
        if "error" in result:
            logger.error(f"Vision API error: {result['error']}")
            return None

        annotation = result.get("fullTextAnnotation", {})
        text = annotation.get("text", "")

        if not text:
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "language": None,
                "orientation": 0,
                "raw": data,
            }

        page = annotation.get("pages", [{}])[0]
        confidence = page.get("confidence", 0.0) * 100

        word_count = sum(
            1
            for blk in page.get("blocks", [])
            for para in blk.get("paragraphs", [])
            for _ in para.get("words", [])
        )

        languages = page.get("property", {}).get("detectedLanguages", [])
        language = languages[0].get("languageCode") if languages else None

        orientation = _orientation_from_vision(page)

        return {
            "text": text,
            "confidence": confidence,
            "word_count": word_count,
            "language": language,
            "orientation": orientation,
            "raw": data,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Vision API HTTP error: {e}")
        return None

    except VisionAPIError:
        raise

    except Exception as e:
        logger.error(f"Vision API failed: {e}")
        return None
