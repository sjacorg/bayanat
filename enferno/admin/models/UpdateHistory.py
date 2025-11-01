from enferno.extensions import db
from enferno.utils.base import BaseMixin


class UpdateHistory(db.Model, BaseMixin):
    """Audit log for all system update attempts.

    Records both successful and failed updates for complete audit trail.
    Status values: 'success', 'failed'
    """

    id = db.Column(db.Integer, primary_key=True)
    version_to = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="success")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Relationship to User - nullable for system/scheduled updates
    user = db.relationship("User", backref="update_history")

    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "version_to": self.version_to,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "user": (
                {
                    "id": self.user.id,
                    "username": self.user.username,
                }
                if self.user
                else None
            ),
        }
