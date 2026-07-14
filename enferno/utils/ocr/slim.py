"""Trim OCR raw payloads: drop per-character symbols, keep word text and geometry.

Google Vision returns geometry down to individual characters (word "symbols").
The UI only consumes paragraph/word bounding boxes and word text, so symbols
are dead weight (roughly two thirds of the payload). Used at write time for
new extractions and by `flask ocr slim-raw` to backfill existing rows.
"""


def _slim(node):
    if isinstance(node, dict):
        if "symbols" in node:
            node = dict(node)
            symbols = node.pop("symbols") or []
            node.setdefault("text", "".join(s.get("text", "") for s in symbols))
        return {k: _slim(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_slim(v) for v in node]
    return node


def has_symbols(node) -> bool:
    """True if any nested dict still carries a per-character symbols array."""
    if isinstance(node, dict):
        return "symbols" in node or any(has_symbols(v) for v in node.values())
    if isinstance(node, list):
        return any(has_symbols(v) for v in node)
    return False


def slim_raw(raw):
    """Return a copy of an OCR raw payload without per-character symbols.

    Word text is preserved as word["text"] (existing text keys win).
    Idempotent; non-dict/list input is returned unchanged.
    """
    if not isinstance(raw, (dict, list)):
        return raw
    return _slim(raw)
