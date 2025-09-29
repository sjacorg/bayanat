from typing import Any

from enferno.extensions import db
from enferno.utils.base import BaseMixin


class SystemInfo(db.Model, BaseMixin):
    """Model for storing system information as key-value pairs."""

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        """Return a dictionary of all system info key-value pairs."""
        entries = cls.query.all()
        return {entry.key: entry.value for entry in entries}

    @classmethod
    def get_value(cls, key: str) -> Any:
        """Get the value associated with a specific key."""
        entry = cls.query.filter_by(key=key).first()
        return entry.value if entry else None


class MigrationHistory(db.Model, BaseMixin):
    """Model for storing applied database migrations."""

    id = db.Column(db.Integer, primary_key=True)
    migration_file = db.Column(db.String(255), unique=True, nullable=False)

    @classmethod
    def is_applied(cls, migration_file: str, session) -> bool:
        """Check if a specific migration file has been applied.

        Convention: migration_history table exists (created during initial deployment).

        Args:
            migration_file: Name of the migration file to check
            session: Session to use (required for transaction consistency).
        """
        return session.query(cls).filter_by(migration_file=migration_file).first() is not None

    @classmethod
    def record_migration(cls, migration_file: str, session):
        """Record a migration file as applied.

        Convention: Always called within a transaction with a session provided.

        Args:
            migration_file: Name of the migration file
            session: Session to use (required - caller manages transaction).
        """
        migration = cls(migration_file=migration_file)
        session.add(migration)
        # Transaction boundary handles the commit
