from typing import Any, Optional

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import ItobInfo

logger = get_logger()


class Itob(db.Model, BaseMixin):
    """
    Incident to bulletin relations model
    """

    extend_existing = True

    # Available Backref: incident
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Available Backref: bulletin
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itobs", foreign_keys=[user_id])

    @property
    def relation_info(self):
        related_info = (
            ItobInfo.query.filter(ItobInfo.id == self.related_as).first()
            if self.related_as
            else None
        )
        # Return the to_dict representation of the related_info if it exists, or an empty dictionary if not
        return related_info.to_dict() if related_info else {}

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the relation."""
        return {
            "bulletin": self.bulletin.to_compact(),
            "incident": self.incident.to_compact(),
            "related_as": self.related_as,
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data
    def from_json(self, relation: Optional[dict[str, Any]] = None) -> "Itob":
        """
        Update the relationship data.

        Args:
            - relation: the relation dictionary.

        Returns:
            - the updated object.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self
