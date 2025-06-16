"""Centralized optional dependency management"""

import logging

logger = logging.getLogger(__name__)
# Feature flags
HAS_WHISPER = False
HAS_TESSERACT = False
# Whisper + torch (both needed for transcription)
try:
    import whisper
    import torch
    from whisper.tokenizer import TO_LANGUAGE_CODE

    HAS_WHISPER = True
except ImportError:
    TO_LANGUAGE_CODE = {}  # Language mapping for transcription
    logger.info("Whisper/torch not available - transcription disabled")
# Tesseract
try:
    import pytesseract

    HAS_TESSERACT = True
except ImportError:
    logger.info("Tesseract not available - OCR disabled")
