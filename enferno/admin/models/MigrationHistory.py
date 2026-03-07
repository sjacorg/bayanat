from enferno.extensions import db


class MigrationHistory(db.Model):
    """Tracks which SQL migration files have been applied."""

    __tablename__ = "migration_history"

    id = db.Column(db.Integer, primary_key=True)
    migration_file = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    @classmethod
    def record(cls, migration_file, session):
        """Record a migration as applied."""
        session.add(cls(migration_file=migration_file))
