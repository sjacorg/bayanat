from typing import Any, Optional

from sqlalchemy import func, update

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class LocationAdminLevel(db.Model, BaseMixin):
    """
    SQL Alchemy model for location admin levels.

    Levels are scoped by hierarchy. A null hierarchy is the legacy global set
    that every existing installation already has, and remains the default.
    """

    __table_args__ = (
        # global defaults need their own guard: a plain composite unique index
        # treats every NULL hierarchy as distinct and would allow duplicates
        db.Index(
            "ix_location_admin_level_legacy_code",
            "code",
            unique=True,
            postgresql_where=db.text("hierarchy_id IS NULL"),
        ),
        db.Index(
            "ix_location_admin_level_hierarchy_code",
            "hierarchy_id",
            "code",
            unique=True,
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String)
    display_order = db.Column(db.Integer)
    hierarchy_id = db.Column(db.Integer, db.ForeignKey("location_hierarchy.id"))
    hierarchy = db.relationship("LocationHierarchy")

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location admin level."""
        return {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "display_order": self.display_order,
            "hierarchy": self.hierarchy.to_dict() if self.hierarchy else None,
            # flat label so lists and dropdowns can disambiguate duplicate codes
            "hierarchy_title": self.hierarchy.title if self.hierarchy else None,
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
        self.hierarchy_id = LocationAdminLevel.hierarchy_id_of(jsn)

    @staticmethod
    def hierarchy_id_of(jsn: dict[str, Any]) -> Optional[int]:
        """Read the hierarchy out of a payload, sent either flat or as the serialized object."""
        return jsn.get("hierarchy_id") or (jsn.get("hierarchy") or {}).get("id")

    @staticmethod
    def in_hierarchy(hierarchy_id: Optional[int]):
        """
        Query for the levels of one hierarchy, or the legacy globals when null.

        Args:
            - hierarchy_id: the hierarchy to scope by, None for legacy levels.

        Returns:
            - a query restricted to that hierarchy.
        """
        return LocationAdminLevel.query.filter(
            LocationAdminLevel.hierarchy_id.is_not_distinct_from(hierarchy_id)
        )

    @staticmethod
    def max_code(hierarchy_id: Optional[int]) -> int:
        """
        Highest level code inside one hierarchy, 0 when it has no levels yet.

        Args:
            - hierarchy_id: the hierarchy to scope by, None for legacy levels.
        """
        return (
            LocationAdminLevel.in_hierarchy(hierarchy_id)
            .with_entities(func.max(LocationAdminLevel.code))
            .scalar()
            or 0
        )

    @staticmethod
    def reorder(ids: list[int], hierarchy_id: Optional[int] = None):
        """
        Reorder the display_order of one hierarchy's location admin levels.
        Does not support partial updates or mixed hierarchies.

        Args:
            - ids: the list of ids to reorder.
            - hierarchy_id: the hierarchy the ids must all belong to.
        """
        known = {
            id
            for (id,) in LocationAdminLevel.in_hierarchy(hierarchy_id).with_entities(
                LocationAdminLevel.id
            )
        }
        # length matters as well as membership: [a, a, b] satisfies set equality
        # against {a, b} and would renumber a twice, leaving a gap in the order
        if len(ids) != len(known) or set(ids) != known:
            raise ValueError("Reorder requires the complete level set of a single hierarchy")

        # one statement, one transaction: a half applied order would silently
        # reshuffle every full_location built from this hierarchy
        db.session.execute(
            update(LocationAdminLevel),
            [{"id": id, "display_order": i + 1} for i, id in enumerate(ids)],
        )
        db.session.commit()
