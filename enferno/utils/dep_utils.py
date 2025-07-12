class DependencyUtils:
    """Simple singleton utility to check for optional dependencies."""

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            # Initialize checks on first creation
            cls._instance._check_dependencies()
        return cls._instance

    def _check_dependencies(self):
        """Check for optional dependencies once during initialization."""
        try:
            import whisper
            import torch

            self.has_whisper = True
        except ImportError:
            self.has_whisper = False

        try:
            import pytesseract

            self.has_tesseract = True
        except ImportError:
            self.has_tesseract = False


# Create singleton instance
dep_utils = DependencyUtils()
