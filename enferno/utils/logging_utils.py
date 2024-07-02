import glob
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from traceback import format_exception
from enferno.settings import Config
import re
from datetime import datetime
import os

cfg = Config()


class JsonFormatter(logging.Formatter):
    """A custom formatter to output log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.

        Args:
            - record: The log record to format.

        Returns:
            - The formatted log record as a JSON string.
        """
        record_dict = {
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.getMessage(),
            "pathname": os.path.relpath(record.pathname),
            "lineno": record.lineno,
        }
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            record_dict["exception"] = {
                "type": str(exc_type.__name__),
                "message": str(exc_value),
                "traceback": "".join(format_exception(exc_type, exc_value, exc_traceback)),
            }
        return json.dumps(record_dict)


def get_logger():
    """Get a logger instance."""
    logger = logging.getLogger("app_logger")
    logger.setLevel(cfg.LOG_LEVEL)

    handler = TimedRotatingFileHandler(
        os.path.join(cfg.LOG_DIR, cfg.LOG_FILE),
        when="midnight",
        backupCount=cfg.LOG_BACKUP_COUNT,
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    return logger


def get_log_filenames():
    """Get a list of log filenames sorted by date."""
    # Get all log files in the log directory
    files = glob.glob(f"{cfg.LOG_FILE}*", root_dir=cfg.LOG_DIR)
    return sort_log_files(files)


def sort_log_files(log_files: list[str]) -> list[str]:
    """
    Sort a list of log files by date at the end of filenames.

    Args:
        - log_files: A list of log file names ending in YYYY-MM-DD.

    Returns:
        - The list of log file names sorted by date.
    """

    def sorting_key(filename):
        match = re.search(r"\.(\d{4}-\d{2}-\d{2})$", filename)
        if match:
            date_string = match.group(1)
            return -datetime.strptime(date_string, "%Y-%m-%d").toordinal()
        else:
            return float("-inf")

    log_files.sort(key=sorting_key)
    return log_files
