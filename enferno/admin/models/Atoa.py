from typing import Any, Optional, Union

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.admin.models.utils import check_relation_roles

logger = get_logger()


class Atoa(db.Model, BaseMixin):
    """
    Actor to actor relationship model
    """

    extend_existing = True

    # This constraint will make sure only one relationship exists across bulletins (and prevent self relation)
    __table_args__ = (db.CheckConstraint("actor_id < related_actor_id"),)

    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)
    related_actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_atoas", foreign_keys=[user_id])

    @property
    def relation_info(self) -> dict[str, Any]:
        related_info = (
            AtoaInfo.query.filter(AtoaInfo.id == self.related_as).first()
            if self.related_as
            else None
        )
        # Return the to_dict representation of the related_info if it exists, or an empty dictionary if not
        return related_info.to_dict() if related_info else {}

    # helper method to check if two actors are related and returns the relationship
    @staticmethod
    def are_related(a_id: t.id, b_id: t.id) -> Union["Atoa", bool]:
        """
        Check if two actors are related.

        Args:
            - a_id: the id of the first actor.
            - b_id: the id of the second actor.

        Returns:
            - the relation if the actors are related, False otherwise.
        """
        if a_id == b_id:
            return False

        # with our id constraint set, just check if there is relation from the lower id to the upper id
        f, t = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        relation = Atoa.query.get((f, t))
        if relation:
            return relation
        else:
            return False

    # given one actor id, this method will return the other related actor id
    def get_other_id(self, id: t.id) -> Optional[t.id]:
        """
        Return the other actor id.

        Args:
            - id: the id of the actor.

        Returns:
            - the other actor id or None.
        """
        if id in (self.actor_id, self.related_actor_id):
            return self.actor_id if id == self.related_actor_id else self.related_actor_id
        return None

    # Create and return a relation between two actors making sure the relation goes from the lower id to the upper id
    # a = 12 b = 11
    @staticmethod
    def relate(a, b):
        f, t = min(a.id, b.id), max(a.id, b.id)

        return Atoa(actor_id=f, related_actor_id=t)

    # Exclude the primary actor from output to get only the related/relating actor

    # custom serialization method
    @check_relation_roles
    def to_dict(self, exclude: Optional["Actor"] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the relation.

        Args:
            - exclude: the actor to exclude.

        Returns:
            - the dictionary representation of the relation.
        """
        if not exclude:
            return {
                "actor_from": self.actor_from.to_compact(),
                "actor_to": self.actor_to.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }
        else:
            actor = self.actor_to if exclude == self.actor_from else self.actor_from
            return {
                "actor": actor.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation: dict[str, Any] = None) -> "Atoa":
        """
        Return a dictionary representation of the relation.

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

    def from_etl(self, json):
        pass
