from typing import Any, Optional, Union

from sqlalchemy import ARRAY

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import BtobInfo, Bulletin
from enferno.admin.models.utils import check_relation_roles

logger = get_logger()


class Btob(db.Model, BaseMixin):
    """
    Bulletin to bulletin relationship model
    """

    extend_existing = True

    # This constraint will make sure only one relationship exists across bulletins (and prevent self relation)
    __table_args__ = (db.CheckConstraint("bulletin_id < related_bulletin_id"),)

    # Source Bulletin
    # Available Backref: bulletin_from
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Target Bulletin
    # Available Backref: bulletin_to
    related_bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(ARRAY(db.Integer))
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_btobs", foreign_keys=[user_id])

    @property
    def relation_info(self) -> list[dict[str, Any]]:
        """
        Return the relation information.

        Returns:
            - the relation information.
        """
        related_infos = (
            BtobInfo.query.filter(BtobInfo.id.in_(self.related_as)).all() if self.related_as else []
        )
        # Return the to_dict representation of each of them
        return [info.to_dict() for info in related_infos]

    # Check if two bulletins are related , if so return the relation, otherwise false
    @staticmethod
    def are_related(a_id: t.id, b_id: t.id) -> Union["Btob", bool]:
        """
        Check if two bulletins are related.

        Args:
            - a_id: the id of the first bulletin.
            - b_id: the id of the second bulletin.

        Returns:
            - the relation if the bulletins are related, False otherwise.
        """
        if a_id == b_id:
            return False

        # with our id constraint set, just check if there is relation from the lower id to the upper id
        f, t = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        relation = Btob.query.get((f, t))
        if relation:
            return relation
        else:
            return False

    # Give an id, get the other bulletin id (relating in or out)
    def get_other_id(self, id: t.id) -> Optional[t.id]:
        """
        Return the other bulletin id.

        Args:
            - id: the id of the bulletin.

        Returns:
            - the other bulletin id or None.
        """
        if id in (self.bulletin_id, self.related_bulletin_id):
            return self.bulletin_id if id == self.related_bulletin_id else self.related_bulletin_id
        return None

    # Create and return a relation between two bulletins making sure the relation goes from the lower id to the upper id
    @staticmethod
    def relate(a: "Bulletin", b: "Bulletin") -> "Btob":
        """
        Create a relation between two bulletins making sure the relation goes from the lower id to the upper id.

        Args:
            - a: the first bulletin.
            - b: the second bulletin.

        Returns:
            - the relation between the two bulletins.
        """
        f, t = min(a.id, b.id), max(a.id, b.id)
        return Btob(bulletin_id=f, related_bulletin_id=t)

    @staticmethod
    def relate_by_id(a: t.id, b: t.id) -> "Btob":
        """
        Relate two bulletins by their ids.

        Args:
            - a: the id of the first bulletin.
            - b: the id of the second bulletin.

        Returns:
            - the created relation between the two bulletins.
        """
        f, t = min(a, b), max(a, b)
        return Btob(bulletin_id=f, related_bulletin_id=t)

    # Exclude the primary bulletin from output to get only the related/relating bulletin
    @check_relation_roles
    def to_dict(self, exclude: Optional["Bulletin"] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the relation.

        Args:
            - exclude: the bulletin to exclude.

        Returns:
            - the dictionary representation of the relation.
        """
        if not exclude:
            return {
                "bulletin_from": self.bulletin_from.to_compact(),
                "bulletin_to": self.bulletin_to.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }
        else:
            bulletin = self.bulletin_to if exclude == self.bulletin_from else self.bulletin_from

            return {
                "bulletin": bulletin.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation: Optional[dict] = None) -> "Btob":
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
