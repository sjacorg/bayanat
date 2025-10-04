"""Database connection utilities."""

from sqlalchemy.engine.url import make_url

from enferno.utils.logging_utils import get_logger

logger = get_logger()


def parse_pg_uri(db_uri: str) -> dict:
    """Parse PostgreSQL URI into connection parameters."""
    if not db_uri:
        return {"username": None, "password": None, "host": None, "port": None, "dbname": None}

    try:
        url = make_url(db_uri)
        return {
            "username": url.username,
            "password": url.password,
            "host": url.host,
            "port": url.port,
            "dbname": url.database,
        }
    except Exception as e:
        logger.error(f"Error parsing database URI: {e}")
        return {"username": None, "password": None, "host": None, "port": None, "dbname": None}
