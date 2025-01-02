from typing import Any, Optional

from sqlalchemy import ARRAY

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import AtobInfo

logger = get_logger()


class Atob(db.Model, BaseMixin):
    """
    Actor to bulletin relationship model
    """

    extend_existing = True

    # Available Backref: bulletin
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Available Backref: actor
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)

    # Relationship extra fields
    # enabling multiple relationship types
    related_as = db.Column(ARRAY(db.Integer))
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_atobs", foreign_keys=[user_id])

    # Exclude the primary bulletin from output to get only the related/relating bulletin
    @property
    def relation_info(self) -> list[dict[str, Any]]:
        # Query the AtobInfo table based on the related_as list
        related_infos = (
            AtobInfo.query.filter(AtobInfo.id.in_(self.related_as)).all() if self.related_as else []
        )
        # Return the to_dict representation of each of them
        return [info.to_dict() for info in related_infos]

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the relation."""
        return {
            "bulletin": self.bulletin.to_compact(),
            "actor": self.actor.to_compact(),
            "related_as": self.related_as or [],
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data
    def from_json(self, relation: Optional[dict[str, Any]] = None) -> "Atob":
        """
        Update the relationship data.

        Args:
            - relation: the relation data.

        Returns:
            - the updated relation.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self
