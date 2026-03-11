"""Translation support via Google Translate API or LLM provider."""

import httpx
from flask import current_app

GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


def translate_text(text: str, target_language: str = "fr", source_language: str = None) -> dict:
    """Translate text using the configured provider.

    Returns dict with: translated_text, source_language, target_language.
    Raises RuntimeError on failure.
    """
    if not text or not text.strip():
        raise ValueError("No text to translate")

    provider = current_app.config.get("OCR_PROVIDER", "google_vision")

    if provider == "llm":
        return _translate_llm(text, target_language, source_language)
    return _translate_google(text, target_language, source_language)


def _translate_google(text: str, target_language: str, source_language: str = None) -> dict:
    """Translate via Google Translate API v2."""
    key = current_app.config.get("GOOGLE_VISION_API_KEY")
    if not key:
        raise RuntimeError("Google API key not configured")

    params = {
        "key": key,
        "q": text,
        "target": target_language,
        "format": "text",
    }
    if source_language and source_language != target_language:
        params["source"] = source_language

    response = httpx.post(GOOGLE_TRANSLATE_URL, data=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    translation = data["data"]["translations"][0]
    return {
        "translated_text": translation["translatedText"],
        "source_language": translation.get("detectedSourceLanguage", source_language),
        "target_language": target_language,
    }


def _translate_llm(text: str, target_language: str, source_language: str = None) -> dict:
    """Translate via LLM endpoint using OpenAI-compatible chat completions."""
    base_url = current_app.config.get("LLM_OCR_URL", "http://localhost:11434")
    model = current_app.config.get("LLM_OCR_MODEL", "llava")
    api_key = current_app.config.get("LLM_OCR_API_KEY")

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    source_hint = f" from {source_language}" if source_language else ""
    prompt = (
        f"Translate the following text{source_hint} to {target_language}. "
        f"Return ONLY the translated text, nothing else.\n\n{text}"
    )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
    response.raise_for_status()
    data = response.json()

    translated = data["choices"][0]["message"]["content"].strip()

    return {
        "translated_text": translated,
        "source_language": source_language,
        "target_language": target_language,
    }
