from typing import Any, Optional

from sqlalchemy import ARRAY

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import ItoaInfo


logger = get_logger()


class Itoa(db.Model, BaseMixin):
    """
    Incident to actor relationship model
    """

    extend_existing = True

    # Available Backref: actor
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)

    # Available Backref: incident
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(ARRAY(db.Integer))
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itoas", foreign_keys=[user_id])

    @property
    def relation_info(self):
        # Query the AtobInfo table based on the related_as list
        related_infos = (
            ItoaInfo.query.filter(ItoaInfo.id.in_(self.related_as)).all() if self.related_as else []
        )
        # Return the to_dict representation of each of them
        return [info.to_dict() for info in related_infos]

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the relation."""
        return {
            "actor": self.actor.to_compact(),
            "incident": self.incident.to_compact(),
            "related_as": self.related_as,
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data, (populates it from json dict)
    def from_json(self, relation: Optional[dict[str, Any]] = None) -> "Itoa":
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
