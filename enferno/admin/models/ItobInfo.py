from typing import Any

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class ItobInfo(db.Model, BaseMixin):
    """
    Itob Relation Information Model
    """

    extend_existing = True

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    reverse_title = db.Column(db.String, nullable=True)
    title_tr = db.Column(db.String)
    reverse_title_tr = db.Column(db.String)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the relation information."""
        return {
            "id": self.id,
            "title": self.title,
            "reverse_title": self.reverse_title,
            "title_tr": self.title_tr,
            "reverse_title_tr": self.reverse_title_tr,
        }

    def from_json(self, jsn: dict[str, Any]) -> "ItobInfo":
        """
        Populate the object from a json dictionary.

        Args:
            - jsn: the json dictionary.

        Returns:
            - the updated object.
        """
        self.title = jsn.get("title", self.title)
        self.reverse_title = jsn.get("reverse_title", self.reverse_title)
        self.title_tr = jsn.get("title_tr", self.title_tr)
        self.reverse_title_tr = jsn.get("reverse_title_tr", self.reverse_title_tr)


# Incident to actor uni-direction relation
