from typing import Any

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class LocationAdminLevel(db.Model, BaseMixin):
    """
    SQL Alchemy model for location admin levels
    """

    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer, nullable=False, unique=True)
    title = db.Column(db.String)
    display_order = db.Column(db.Integer)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location admin level."""
        return {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "display_order": self.display_order,
        }

    def from_json(self, jsn: dict[str, Any]) -> "LocationAdminLevel":
        """
        Create a location admin level object from a json dictionary.

        Args:
            - json: the json dictionary to create the location admin level from.
        """
        self.code = jsn.get("code")
        self.title = jsn.get("title")
        self.display_order = jsn.get("display_order", 0)

    @staticmethod
    def reorder(ids: list[int]):
        """
        Reorder the display_order of the location admin levels.
        Does not support partial updates.
        Args:
            - ids: the list of ids to reorder.
        """
        idset = set(ids)
        if len(idset) != LocationAdminLevel.query.count():
            raise ValueError("Not all location admin levels exist")

        for i, id in enumerate(ids):
            lal = LocationAdminLevel.query.get(id)
            lal.display_order = i + 1
            if not lal.save(raise_exception=True):
                raise ValueError("Error updating location admin level display order")
