class DependencyUtils:
    HAS_WHISPER = None
    HAS_TESSERACT = None
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DependencyUtils, cls).__new__(cls)
            cls._instance.HAS_WHISPER = cls._instance.check_whisper()
            cls._instance.HAS_TESSERACT = cls._instance.check_tesseract()
        return cls._instance

    @classmethod
    def check_whisper(cls):
        if cls.HAS_WHISPER is None:
            try:
                import whisper
                import torch

                cls.HAS_WHISPER = True
            except ImportError:
                cls.HAS_WHISPER = False
        return cls.HAS_WHISPER

    @classmethod
    def check_tesseract(cls):
        if cls.HAS_TESSERACT is None:
            try:
                import pytesseract

                cls.HAS_TESSERACT = True
            except ImportError:
                cls.HAS_TESSERACT = False
        return cls.HAS_TESSERACT


DependencyUtils()
