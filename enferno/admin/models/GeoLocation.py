from typing import Any

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class GeoLocation(db.Model, BaseMixin):
    """
    SQL Alchemy model for Geo markers (improved location class)
    """

    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    type_id = db.Column(db.Integer, db.ForeignKey("geo_location_types.id"))
    type = db.relationship("GeoLocationType", backref="geolocations")  # Added a relationship
    main = db.Column(db.Boolean)
    latlng = db.Column(Geometry("POINT", srid=4326))
    comment = db.Column(db.Text)
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"))

    def from_json(self, jsn: dict[str, Any]) -> "GeoLocation":
        """
        Create a geo location object from a json dictionary.

        Args:
            - json: the json dictionary to create the geo location from.

        Returns:
            - the geo location object.
        """
        self.title = jsn.get("title")
        geotype = jsn.get("geotype")
        if geotype and (id := geotype.get("id")):
            self.type_id = id
        self.main = jsn.get("main")
        self.latlng = f'POINT({jsn.get("lng")} {jsn.get("lat")})'
        self.comment = jsn.get("comment")
        return self

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the geo location."""
        return {
            "id": self.id,
            "title": self.title,
            "geotype": self.type.to_dict() if self.type else None,
            "main": self.main,
            "lat": to_shape(self.latlng).y,
            "lng": to_shape(self.latlng).x,
            "comment": self.comment,
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }
