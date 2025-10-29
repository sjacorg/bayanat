from enferno.extensions import db
from enferno.utils.base import BaseMixin


class UpdateHistory(db.Model, BaseMixin):
    """Audit log for completed system updates."""

    id = db.Column(db.Integer, primary_key=True)
    version_to = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "version_to": self.version_to,
            "created_at": self.created_at.isoformat(),
        }
