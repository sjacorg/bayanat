from typing import Any

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class LocationType(db.Model, BaseMixin):
    """
    SQL Alchemy model for location types
    """

    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location type."""
        return {"id": self.id, "title": self.title, "description": self.description}

    def from_json(self, jsn: dict[str, Any]) -> "LocationType":
        """
        Create a location type object from a json dictionary.

        Args:
            - json: the json dictionary to create the location type from.
        """
        self.title = jsn.get("title")
        self.description = jsn.get("description")
