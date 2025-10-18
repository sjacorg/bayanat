from datetime import datetime
from typing import Any, Optional
import arrow
from dateutil.parser import parse
from flask import current_app

from enferno.utils.logging_utils import get_logger

logger = get_logger()


class DateHelper:
    """Helper class for date operations."""

    @staticmethod
    def serialize_datetime(dt: Any) -> Optional[str]:
        """
        Return a serialized datetime string in the format "YYYY-MM-DDTHH:mm".

        Args:
            - dt (Any): The datetime to serialize.

        Returns:
            - str: The serialized datetime string.
        """
        return arrow.get(dt).format("YYYY-MM-DDTHH:mm") if dt else None

    @staticmethod
    def file_date_parse(dt: Any) -> Optional[str]:
        """
        Return a serialized datetime string in the format "YYYY-MM-DDTHH:mm".

        Args:
            - dt (Any): The datetime to serialize.

        Returns:
            - str: The serialized datetime string.
        """
        try:
            d = arrow.get(dt, "YYYY:MM:DD HH:mm:ss").format("YYYY-MM-DDTHH:mm") if dt else None
            return d
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @staticmethod
    def parse_datetime(dt: Any) -> Optional[datetime]:
        """
        Parse a datetime string in the format "YYYY-MM-DDTHH:mm" or "YYYY-MM-DDTHH:mm:ss".

        Args:
            - dt (Any): The datetime string to parse.

        Returns:
            - datetime: The parsed datetime object.
        """
        if not dt:
            return None

        try:
            # Try with seconds first (more specific)
            d = arrow.get(dt, "YYYY-MM-DDTHH:mm:ss").datetime.replace(tzinfo=None)
            return d
        except Exception:
            try:
                # Fall back to format without seconds
                d = arrow.get(dt, "YYYY-MM-DDTHH:mm").datetime.replace(tzinfo=None)
                return d
            except Exception as e:
                logger.error(e, exc_info=True)
                return None

    @staticmethod
    def parse_date(str_date: str) -> Optional[str]:
        """
        Parse a date string in any format.

        Args:
            - str_date (str): The date string to parse.

        Returns:
            - str: The parsed date string.
        """
        # Handle pandas naT (null dates values)
        if str_date != str_date:
            return None
        try:
            d = parse(str(str_date))
            return str(d)
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
