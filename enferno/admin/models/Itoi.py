from typing import Any, Optional, Union

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import ItoiInfo
from enferno.admin.models.utils import check_relation_roles

logger = get_logger()


class Itoi(db.Model, BaseMixin):
    """
    Incident to incident relation model
    """

    extend_existing = True

    # This constraint will make sure only one relationship exists across bulletins (and prevent self relation)
    __table_args__ = (db.CheckConstraint("incident_id < related_incident_id"),)

    # Source Incident
    # Available Backref: incident_from
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Target Incident
    # Available Backref: Incident_to
    related_incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itois", foreign_keys=[user_id])

    @property
    def relation_info(self):
        related_info = (
            ItoiInfo.query.filter(ItoiInfo.id == self.related_as).first()
            if self.related_as
            else None
        )
        # Return the to_dict representation of the related_info if it exists, or an empty dictionary if not
        return related_info.to_dict() if related_info else {}

    # Check if two incidents are related , if so return the relation, otherwise false
    @staticmethod
    def are_related(a_id: t.id, b_id: t.id) -> Union["Itoi", bool]:
        """
        Check if two incidents are related.

        Args:
            - a_id: the first incident id.
            - b_id: the second incident id.

        Returns:
            - the relationship if it exists, or False.
        """
        if a_id == b_id:
            return False

        # with our id constraint set, just check if there is relation from the lower id to the upper id
        f, t = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        relation = Itoi.query.get((f, t))
        if relation:
            return relation
        else:
            return False

    # Give an id, get the other bulletin id (relating in or out)
    def get_other_id(self, id: t.id) -> Optional[t.id]:
        """
        Get the other incident id.

        Args:
            - id: the incident id.

        Returns:
            - the other incident id if it exists, or None.
        """
        if id in (self.incident_id, self.related_incident_id):
            return self.incident_id if id == self.related_incident_id else self.related_incident_id
        return None

    # Create and return a relation between two bulletins making sure the relation goes from the lower id to the upper id
    @staticmethod
    def relate(a: "Incident", b: "Incident") -> "Itoi":
        """
        Create a relationship between two incidents.

        Args:
            - a: the first incident.
            - b: the second incident.

        Returns:
            - the relationship.
        """
        f, t = min(a.id, b.id), max(a.id, b.id)
        return Itoi(incident_id=f, related_incident_id=t)

    # custom serialization method
    @check_relation_roles
    def to_dict(self, exclude: Optional["Incident"] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the relation.

        Args:
            - exclude: the incident to exclude.

        Returns:
            - the dictionary representation of the relation.
        """
        if not exclude:
            return {
                "incident_from": self.incident_from.to_compact(),
                "incident_to": self.incident_to.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }
        else:
            incident = self.incident_to if exclude == self.incident_from else self.incident_from
            return {
                "incident": incident.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation: dict[str, Any] = None) -> "Itoi":
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
