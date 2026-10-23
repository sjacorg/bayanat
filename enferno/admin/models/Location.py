import json
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import Any, Optional

from flask import current_app, has_app_context
import pandas as pd
import werkzeug
from flask_login import current_user
from geoalchemy2 import Geometry, Geography
from geoalchemy2.shape import to_shape
from sqlalchemy import ARRAY, func, text

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


def _walk(seed: str, seed_path: str) -> str:
    """A recursive `tree` CTE from the seed rows down, each row carrying its path to the root."""
    return f"""
    tree AS (
        SELECT id, title, postal_code, admin_level_id, parent_id, {seed_path} AS path
        FROM location WHERE {seed}
        UNION ALL
        SELECT c.id, c.title, c.postal_code, c.admin_level_id, c.parent_id, c.id || t.path
        FROM location c JOIN tree t ON c.parent_id = t.id
        -- a pre-existing cycle would otherwise recurse until the statement times out
        WHERE NOT c.id = ANY(t.path)
    )"""


# what full_location and id_tree should hold for every row of `tree`
_EXPECTED_PATHS = """
    expected AS (
        SELECT t.id,
            CASE
                WHEN t.parent_id IS NULL OR t.admin_level_id IS NULL THEN
                    CASE WHEN :postal_code AND t.postal_code IS NOT NULL
                         THEN t.title || ' ' || t.postal_code ELSE t.title END
                ELSE (
                    -- levels without a display_order (a fresh install seeds none) fall back
                    -- to tree order, root first, instead of an arbitrary one
                    SELECT string_agg(loc.title, ', '
                                      ORDER BY la.display_order NULLS LAST, ids.ord DESC)
                    FROM unnest(t.path) WITH ORDINALITY AS ids(id, ord)
                    JOIN location loc ON loc.id = ids.id
                    LEFT JOIN location_admin_level la ON loc.admin_level_id = la.id
                ) || CASE WHEN :postal_code AND t.postal_code IS NOT NULL
                          THEN ' ' || t.postal_code ELSE '' END
            END AS full_string,
            (
                SELECT string_agg('[' || ids.id || ']', ' ' ORDER BY ids.ord)
                FROM unnest(t.path) WITH ORDINALITY AS ids(id, ord)
            ) AS id_string
        FROM tree t
    )"""

_APPLY_PATHS = """
    UPDATE location l SET full_location = e.full_string, id_tree = e.id_string
    FROM expected e WHERE l.id = e.id"""


class Location(db.Model, BaseMixin):
    """
    SQL Alchemy model for locations
    """

    CELERY_FLAG = "tasks:locations:fullpath:status"

    COLOR = "#ff663366"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("location.id"))
    parent = db.relationship("Location", remote_side=id, backref="child_locations")
    title = db.Column(db.String)
    title_ar = db.Column(db.String)
    location_type_id = db.Column(db.Integer, db.ForeignKey("location_type.id"))
    location_type = db.relationship("LocationType", foreign_keys=[location_type_id])
    latlng = db.Column(Geometry("POINT", srid=4326))
    admin_level_id = db.Column(db.Integer, db.ForeignKey("location_admin_level.id"))
    admin_level = db.relationship("LocationAdminLevel", foreign_keys=[admin_level_id])
    description = db.Column(db.Text)
    postal_code = db.Column(db.String)

    country_id = db.Column(db.Integer, db.ForeignKey("countries.id"))
    country = db.relationship("Country", backref="locations")

    tags = db.Column(ARRAY(db.String))
    full_location = db.Column(db.String)
    id_tree = db.Column(db.String)

    def create_revision(self, user_id: Optional[t.id] = None, created: Optional[datetime] = None):
        """
        Create a revision of the current location.

        Args:
            - user_id: the user id to associate with the revision.
            - created: the creation date of the revision.
        """
        # Local import: at package import time, LocationHistory in the module-level
        # import above is bound to the submodule (not the class) due to circular imports.
        from enferno.admin.models import LocationHistory  # noqa: F401, F811

        if not user_id:
            user_id = getattr(current_user, "id", 1)
        l = LocationHistory(location_id=self.id, data=self.to_dict(), user_id=user_id)
        if created:
            l.created_at = created
            l.updated_at = created
        l.save()

    def get_children_ids(self) -> list:
        """
        Get the ids of the children of the current location.

        Returns:
            - list of children ids.
        """
        children = (
            Location.query.with_entities(Location.id)
            .filter(Location.id_tree.like(f"%[{self.id}]%"))
            .all()
        )
        # leaf children will return at least their id
        return [x[0] for x in children]

    @staticmethod
    def get_children_by_id(id: t.id) -> list:
        """
        Get the children of the location with the given id.

        Args:
            - id: the id of the location.

        Returns:
            - list of children locations.
        """
        children = (
            Location.query.with_entities(Location.id)
            .filter(Location.id_tree.like(f"%[{id}]%"))
            .all()
        )
        # leaf children will return at least their id
        return [x[0] for x in children]

    @staticmethod
    def find_by_title(title: str) -> Optional["Location"]:
        """
        Find the first location with the given title.

        Args:
            - title: the title of the location.

        Returns:
            - the location object.
        """
        ar = Location.query.filter(Location.title_ar.ilike(title)).first()
        if ar:
            return ar
        else:
            return Location.query.filter(Location.title.ilike(title)).first()

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location."""

        return {
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar,
            "description": self.description,
            "location_type": self.location_type.to_dict() if self.location_type else "",
            "admin_level": self.admin_level.to_dict() if self.admin_level else "",
            "latlng": (
                {"lng": to_shape(self.latlng).x, "lat": to_shape(self.latlng).y}
                if self.latlng
                else None
            ),
            "postal_code": self.postal_code,
            "country": self.country.to_dict() if self.country else None,
            "parent": self.to_parent_dict(),
            "tags": self.tags or [],
            "lat": to_shape(self.latlng).y if self.latlng else None,
            "lng": to_shape(self.latlng).x if self.latlng else None,
            "full_location": self.full_location,
            "full_string": "{} | {}".format(self.full_location or "", self.title_ar or ""),
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }

    def to_parent_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of current object's parent."""
        if not self.parent:
            return None
        else:
            return {
                "id": self.parent_id,
                "title": self.parent.title,
                "full_string": "{} | {}".format(
                    self.parent.full_location or "", self.parent.title_ar or ""
                ),
                "admin_level": self.parent.admin_level.to_dict() if self.parent.admin_level else "",
            }

    # custom compact serialization method
    def min_json(self) -> dict[str, Any]:
        """
        Minified JSON representation of the location.

        Returns:
            - dictionary with id, location_type and full_string keys.
        """
        return {
            "id": self.id,
            "location_type": self.location_type.to_dict() if self.location_type else "",
            "full_string": "{} | {}".format(self.full_location, self.title_ar),
        }

    def to_compact(self) -> dict[str, Any]:
        """
        Compact serialization for locations.

        Returns:
            - dictionary with id, title, full_string, lat and lng keys.
        """
        return {
            "id": self.id,
            "title": self.title,
            "full_string": self.full_location,
            "lat": to_shape(self.latlng).y if self.latlng else None,
            "lng": to_shape(self.latlng).x if self.latlng else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the location."""
        return json.dumps(self.to_dict())

    # populate model from json dict
    def from_json(self, jsn: dict[str, Any]) -> "Location":
        """
        Create a location object from a json dictionary.

        Args:
            - json: the json dictionary to create the location from.

        Returns:
            - the location object.
        """
        # Local import: see note on create_revision. Avoids module/class shadowing.
        from enferno.admin.models import LocationType, LocationAdminLevel  # noqa: F401, F811

        self.title = jsn.get("title")
        self.title_ar = jsn.get("title_ar")
        self.description = jsn.get("description")
        if jsn.get("latlng"):
            lng = jsn.get("latlng").get("lng")
            lat = jsn.get("latlng").get("lat")
            self.latlng = f"SRID=4326;POINT({lng} {lat})"
        else:
            self.latlng = None

        # little validation doesn't hurt
        allowed_location_types = [l.title for l in LocationType.query.all()]
        if (
            jsn.get("location_type")
            and jsn.get("location_type").get("title") in allowed_location_types
        ):
            self.location_type_id = jsn.get("location_type").get("id")
            self.location_type = db.session.get(LocationType, self.location_type_id)

            if self.location_type.title == "Administrative Location":
                self.admin_level_id = jsn.get("admin_level").get("id")
                self.admin_level = db.session.get(LocationAdminLevel, self.admin_level_id)
            else:
                self.admin_level_id = None
                self.admin_level = None
        else:
            self.location_type = None

        self.full_location = jsn.get("full_location")
        self.postal_code = jsn.get("postal_code")
        country = jsn.get("country")
        if country and (id := country.get("id")):
            self.country_id = id
        else:
            self.country_id = None
        self.tags = jsn.get("tags", [])
        parent = jsn.get("parent")
        if parent and parent.get("id"):
            self.parent_id = parent.get("id")
        else:
            self.parent_id = None

        return self

    # helper method
    def get_sub_locations(self) -> list:
        """Helper method to get full location hierarchy."""
        if not self.sub_location:
            return [self]
        else:
            locations = [self]
            for l in self.sub_location:
                locations += [l] + l.get_sub_locations()
            return locations

    @staticmethod
    def _include_postal_code() -> bool:
        return has_app_context() and current_app.config.get("LOCATIONS_INCLUDE_POSTAL_CODE", False)

    @staticmethod
    def _write_paths(query: str, **params) -> int:
        """Run one path rewrite in its own transaction and return the rows touched."""
        try:
            result = db.session.execute(
                text(query), {"postal_code": Location._include_postal_code(), **params}
            )
            db.session.commit()
            return result.rowcount
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to rebuild location paths: {str(e)}", exc_info=e)
            raise

    @staticmethod
    def regenerate_all_full_locations() -> None:
        """
        Rebuild full_location and id_tree for every location, in one statement.

        Used by the Regenerate action in system administration. It used to rebuild
        the text only, which is why an import that never generated an ancestor tree
        could leave locations permanently unreachable by ancestor search with no way
        to repair them from the interface.

        Seeded from every root at once rather than looping subtrees: one recursive
        pass over the table instead of one per root, and one transaction, so a
        failure cannot leave half the paths on the old order and half on the new.
        """
        query = f"WITH RECURSIVE {_walk('parent_id IS NULL', 'ARRAY[id]')}, {_EXPECTED_PATHS} {_APPLY_PATHS}"
        count = Location._write_paths(query)
        logger.info(f"Rebuilt location paths for {count} locations.")

    def rebuild_subtree(self) -> None:
        """
        Rebuild full_location and id_tree for this location and every descendant.

        Both columns are denormalized copies of the path from the root, so renaming
        a location or moving it invalidates every row underneath it, not just itself.
        Rebuilding only the edited row leaves descendants holding the old text and,
        worse, the old ancestor chain, which drops them out of ancestor search.
        """
        query = f"""
        WITH RECURSIVE ancestry AS (
            SELECT id, parent_id, ARRAY[id] AS path
            FROM location WHERE id = :id
            UNION ALL
            SELECT p.id, p.parent_id, a.path || p.id
            FROM location p JOIN ancestry a ON p.id = a.parent_id
            WHERE NOT p.id = ANY(a.path)
        ),
        root_path AS (
            SELECT path FROM ancestry ORDER BY array_length(path, 1) DESC LIMIT 1
        ),
        {_walk('id = :id', '(SELECT path FROM root_path)')},
        {_EXPECTED_PATHS}
        {_APPLY_PATHS}
        """
        Location._write_paths(query, id=self.id)

    @staticmethod
    def geo_query_location(target_point: dict[str, Any], radius_in_meters: int) -> Any:
        """
        Geosearch via locations.

        Args:
            - target_point: dictionary with lat and lng keys.
            - radius_in_meters: radius in meters.

        Returns:
            - query object.
        """
        point = func.ST_SetSRID(
            func.ST_MakePoint(target_point.get("lng"), target_point.get("lat")), 4326
        )

        return func.ST_DWithin(
            func.cast(Location.latlng, Geography), func.cast(point, Geography), radius_in_meters
        )

    # imports csv data into db
    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Imports Location data from a CSV file.

        Args:
            - file_storage: the file storage object containing the CSV data.

        Returns:
            - empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        no_df = df.drop("parent_id", axis=1)
        no_df["deleted"] = no_df["deleted"].astype("bool")

        # pick only locations with parents
        df = df[df.parent_id.notnull()]

        # convert parent to int
        df["parent_id"] = df["parent_id"].astype("int")

        # limit data frame to only id/parent_id pairs
        df = df[["id", "parent_id"]]

        # step.1 import locations - no parents
        no_df.to_sql("location", con=db.engine, index=False, if_exists="append")
        logger.info("Locations imported successfully.")

        # step.2 update locations - add parents
        db.session.bulk_update_mappings(Location, df.to_dict(orient="records"))
        db.session.commit()
        logger.info("Locations parents updated successfully.")

        # reset id sequence counter
        max_id = db.session.execute(text("select max(id)+1 from location")).scalar()
        db.session.execute(text("alter sequence location_id_seq restart with :m"), {"m": max_id})
        db.session.commit()

        # bulk inserts bypass the per-edit rebuild, and an import that leaves id_tree
        # empty makes every imported location invisible to ancestor search
        Location.regenerate_all_full_locations()
        logger.info("Location paths regenerated after import.")

        return ""
