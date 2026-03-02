"""OCR provider dispatch."""

PROVIDERS = {
    "google_vision": "enferno.utils.ocr.google_vision",
    "llm": "enferno.utils.ocr.llm",
}


def get_provider(name: str):
    """Return the extract_text function for the given provider name."""
    import importlib

    module_path = PROVIDERS.get(name)
    if not module_path:
        raise ValueError(f"Unknown OCR provider: {name}")
    return importlib.import_module(module_path).extract_text
