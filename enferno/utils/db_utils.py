"""Database utilities."""

from pathlib import Path

from sqlalchemy import text

from enferno.extensions import db

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def ensure_sql_functions():
    """Load all SQL functions from enferno/sql/functions.sql.

    Safe to call multiple times (CREATE OR REPLACE).
    Must run before db.create_all() so generated columns can reference them.
    """
    sql_file = SQL_DIR / "functions.sql"
    with db.engine.connect() as conn:
        conn.execute(text(sql_file.read_text()))
        conn.commit()
