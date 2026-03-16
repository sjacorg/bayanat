import glob
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from traceback import format_exception
from enferno.settings import Config
import re
from datetime import datetime
import os
from traceback import TracebackException
from celery.signals import after_setup_logger, after_setup_task_logger

cfg = Config()
DEFAULT_LOG_LEVEL = "INFO"


class JsonFormatter(logging.Formatter):
    """A custom formatter to output log records as JSON with relative paths."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string with relative paths.

        Args:
            - record: The log record to format.

        Returns:
            - The formatted log record as a JSON string.
        """
        record_dict = {
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "pathname": os.path.relpath(record.pathname),
            "lineno": record.lineno,
        }
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            te = TracebackException(exc_type, exc_value, exc_traceback)

            # Custom formatting of the traceback with relative paths
            formatted_tb = []
            for frame in te.stack:
                formatted_tb.append(
                    f'  File "{os.path.relpath(frame.filename)}", line {frame.lineno}, in {frame.name}\n    {frame.line}'
                )

            record_dict["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "traceback": "Traceback (most recent call last):\n"
                + "\n".join(formatted_tb)
                + f"\n{exc_type.__name__}: {exc_value}",
            }
        return json.dumps(record_dict)


def _file_handler():
    """Build a file handler for logging."""
    handler = TimedRotatingFileHandler(
        os.path.join(cfg.LOG_DIR, cfg.LOG_FILE),
        when="midnight",
        backupCount=cfg.LOG_BACKUP_COUNT,
    )
    handler.setFormatter(JsonFormatter())
    return handler


def _stream_handler():
    """Build a stdout handler for logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    return handler


def get_logger(name="app_logger"):
    """Get a logger instance. File-only for the app process."""
    logger = logging.getLogger(name)
    logger.setLevel(cfg.LOG_LEVEL if cfg.LOG_LEVEL else DEFAULT_LOG_LEVEL)
    logger.propagate = False

    if not logger.handlers:
        if cfg.APP_LOG_ENABLED:
            logger.handlers = [_file_handler()]
        else:
            logger.handlers = [logging.NullHandler()]
    return logger


@after_setup_logger.connect
def setup_celery_logger(logger, *args, **kwargs):
    """Configure Celery logger: file + stdout for live visibility."""
    log_level = cfg.LOG_LEVEL if cfg.LOG_LEVEL else DEFAULT_LOG_LEVEL
    handlers = [_stream_handler()]
    if cfg.CELERY_LOG_ENABLED:
        handlers.append(_file_handler())
    logger.handlers = handlers
    for h in logger.handlers:
        h.setLevel(log_level)
    logger.propagate = False

    # Suppress celery.redirected to prevent SMTP debug output (leaks credentials)
    logging.getLogger("celery.redirected").setLevel(logging.CRITICAL)


@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    """Configure the Celery task logger to use our existing logging setup."""
    setup_celery_logger(logger)


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
