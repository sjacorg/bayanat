"""OCR provider dispatch. Convention: each module exports extract_text()."""

import importlib


def get_provider(name: str):
    """Return the extract_text function for the given provider name."""
    try:
        mod = importlib.import_module(f"enferno.utils.ocr.{name}")
        return mod.extract_text
    except (ModuleNotFoundError, AttributeError):
        raise ValueError(f"Unknown OCR provider: {name}")
