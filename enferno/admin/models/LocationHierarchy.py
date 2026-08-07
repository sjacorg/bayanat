from typing import Any

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class LocationHierarchy(db.Model, BaseMixin):
    """
    SQL Alchemy model for location hierarchies.

    A hierarchy names one operational taxonomy of administrative levels
    (e.g. Palestine: Territory > Governorate > Locality). Installations that
    never create one keep the legacy global levels, which carry no hierarchy.
    """

    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False, unique=True)
    title_tr = db.Column(db.String)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location hierarchy."""
        return {
            "id": self.id,
            "title": self.title,
            "title_tr": self.title_tr,
        }

    def from_json(self, jsn: dict[str, Any]) -> "LocationHierarchy":
        """
        Populate a location hierarchy from a json dictionary.

        Args:
            - jsn: the json dictionary to create the location hierarchy from.
        """
        self.title = jsn.get("title")
        self.title_tr = jsn.get("title_tr")
        return self
