import shutil
from importlib.util import find_spec


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
        self.has_whisper = bool(find_spec("whisper") and find_spec("torch"))
        self.has_tesseract = find_spec("pytesseract") is not None


# Create singleton instance
dep_utils = DependencyUtils()


def require_tools(*names: str) -> None:
    """Raise if any external binary is missing, so imports fail instead of degrading."""
    missing = [name for name in names if not shutil.which(name)]
    if missing:
        raise ValueError(f"{', '.join(missing)} not installed on the server")
