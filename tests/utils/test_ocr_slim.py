"""Tests for OCR raw payload slimming (enferno.utils.ocr.slim)."""

import json

from enferno.utils.ocr.slim import has_symbols, slim_raw


def _word(text, x=0):
    return {
        "boundingBox": {"vertices": [{"x": x, "y": 0}, {"x": x + 50, "y": 0}]},
        "symbols": [
            {
                "text": ch,
                "boundingBox": {"vertices": [{"x": x + i * 10, "y": 0}]},
                "property": {"detectedBreak": {"type": "SPACE"}},
            }
            for i, ch in enumerate(text)
        ],
    }


def _vision_raw():
    return {
        "responses": [
            {
                "fullTextAnnotation": {
                    "text": "hello world",
                    "pages": [
                        {
                            "width": 800,
                            "height": 600,
                            "blocks": [
                                {
                                    "blockType": "TEXT",
                                    "paragraphs": [
                                        {
                                            "boundingBox": {"vertices": [{"x": 0, "y": 0}]},
                                            "property": {
                                                "detectedLanguages": [{"languageCode": "en"}]
                                            },
                                            "words": [_word("hello"), _word("world", x=60)],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            }
        ]
    }


def test_slim_strips_symbols_and_keeps_word_text():
    slim = slim_raw(_vision_raw())
    assert not has_symbols(slim)
    para = slim["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"][0]["paragraphs"][0]
    assert [w["text"] for w in para["words"]] == ["hello", "world"]
    # geometry the overlay uses survives
    assert para["boundingBox"] == {"vertices": [{"x": 0, "y": 0}]}
    assert para["words"][0]["boundingBox"]["vertices"][0] == {"x": 0, "y": 0}
    assert para["property"]["detectedLanguages"][0]["languageCode"] == "en"
    assert slim["responses"][0]["fullTextAnnotation"]["text"] == "hello world"


def test_slim_shrinks_payload():
    raw = _vision_raw()
    assert len(json.dumps(slim_raw(raw))) < len(json.dumps(raw))


def test_slim_is_idempotent():
    slim = slim_raw(_vision_raw())
    assert slim_raw(slim) == slim


def test_slim_does_not_mutate_input():
    raw = _vision_raw()
    slim_raw(raw)
    assert has_symbols(raw)


def test_slim_handles_multipage_pdf_wrapper():
    raw = {"pages": [_vision_raw(), _vision_raw()]}
    slim = slim_raw(raw)
    assert not has_symbols(slim)
    assert len(slim["pages"]) == 2


def test_slim_preserves_existing_word_text():
    word = _word("hi")
    word["text"] = "custom"
    slim = slim_raw({"words": [word]})
    assert slim["words"][0]["text"] == "custom"


def test_slim_passes_through_non_vision_payloads():
    assert slim_raw(None) is None
    assert slim_raw({"error": "OCR failed"}) == {"error": "OCR failed"}
    assert not has_symbols({"error": "OCR failed"})
