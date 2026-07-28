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


class Location(db.Model, BaseMixin):
    """
    SQL Alchemy model for locations
    """

    CELERY_FLAG = "tasks:locations:fullpath:status"

    COLOR = "#ff663366"
    __table_args__ = (
        db.CheckConstraint("parent_id != id", name="location_no_self_parent"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("location.id"), index=True)
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

    def placement_error(self) -> Optional[str]:
        """
        Why this location cannot sit where it has been put, or None if it can.

        `full_location` orders a path by the display_order of its levels, so a path
        that mixes ladders, doubles back on itself, or loops produces text that means
        nothing. Legacy locations carry no hierarchy on either side, so the hierarchy
        rules never fire on an installation that has not created one.

        The parent is read by id rather than through the relationship: on create the
        object is still transient, and the relationship would silently be None.
        """

        loops, above = self._walk_up()
        if loops:
            return "A location cannot be placed under itself or one of its own descendants"

        if self.admin_level and above:
            if self.admin_level.hierarchy_id != above.hierarchy_id:
                return "Parent location belongs to a different hierarchy"
            # code is the structural order and is immutable; display_order is the
            # presentation order, which admins reorder to match an address format
            if above.code >= self.admin_level.code:
                return "Parent location must sit on a level above this one"

        # the same two rules seen from above. Descends past unlevelled children for
        # the same reason the upward walk climbs past unlevelled ancestors: a point
        # of interest in between must not be able to hide a mixed or inverted ladder.
        if self.id and self.admin_level:
            for hierarchy_id, code in self._nearest_levelled_descendants():
                if hierarchy_id != self.admin_level.hierarchy_id:
                    return "Locations under this one belong to a different hierarchy"
                if code <= self.admin_level.code:
                    return "Locations under this one sit on a level at or above this one"

        return None

    def _nearest_levelled_descendants(self):
        """The first levelled location on each branch below this one, as (hierarchy, code)."""
        query = """
        WITH RECURSIVE below AS (
            SELECT id, admin_level_id, ARRAY[id] AS path
            FROM location WHERE parent_id = :id
            UNION ALL
            SELECT c.id, c.admin_level_id, c.id || b.path
            FROM location c JOIN below b ON c.parent_id = b.id
            WHERE b.admin_level_id IS NULL AND NOT c.id = ANY(b.path)
        )
        SELECT la.hierarchy_id, la.code
        FROM below b JOIN location_admin_level la ON la.id = b.admin_level_id;
        """
        return db.session.execute(text(query), {"id": self.id}).all()

    def _walk_up(self):
        """
        Walk the ancestor chain once, answering both questions it can answer.

        Returns (loops, nearest_levelled_ancestor_level). Ancestors without a level
        are skipped rather than ending the walk, which is the plan's rule that a
        non-administrative place takes its hierarchy from the nearest one that has it.
        """
        node = db.session.get(Location, self.parent_id) if self.parent_id else None
        level, seen = None, set()
        while node and node.id not in seen:
            if node.id == self.id:
                return True, level
            if level is None and node.admin_level:
                level = node.admin_level
            seen.add(node.id)
            node = db.session.get(Location, node.parent_id) if node.parent_id else None
        return False, level

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

    # helper method to get full location hierarchy
    def get_full_string(self) -> str:
        """
        Generates full string of location and parents using CTE.
        Args:
            - postal_code: whether to include postal code in result
        Returns:
            - formatted string of location hierarchy
        """
        if not has_app_context():
            postal_code = False
        else:
            postal_code = current_app.config.get("LOCATIONS_INCLUDE_POSTAL_CODE", False)

        self_title = (
            self.title
            if not (postal_code and self.postal_code)
            else self.title + " " + self.postal_code
        )
        if not self.parent_id or self.admin_level is None:
            return self_title
        with db.session.begin_nested():
            try:
                query = """
            WITH RECURSIVE location_tree AS (
                SELECT 
                    l.id,
                    l.title,
                    l.postal_code,
                    l.admin_level_id,
                    l.parent_id,
                    ARRAY[l.id] as path
                FROM location l 
                WHERE l.id = :id
                
                UNION ALL
                
                SELECT
                    p.id,
                    p.title,
                    p.postal_code,
                    p.admin_level_id,
                    p.parent_id,
                    p.id || t.path
                FROM location p
                JOIN location_tree t ON p.id = t.parent_id
            )
            SELECT 
                lt.id,
                lt.title,
                lt.postal_code,
                lt.admin_level_id,
                la.display_order
            FROM location_tree lt
            LEFT JOIN location_admin_level la ON lt.admin_level_id = la.id
            ORDER BY la.display_order NULLS LAST;
            """

                with db.engine.connect() as connection:
                    result = connection.execute(text(query), {"id": self.id})
                locations = [{"title": row.title, "postal_code": row.postal_code} for row in result]

                if not locations:
                    return self_title

                formatted = ", ".join(loc["title"] for loc in locations)
                if postal_code and self.postal_code:
                    formatted += " " + self.postal_code

                return formatted
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to regenerate location strings: {str(e)}", exc_info=e)
                return self_title

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
        query = """
        WITH RECURSIVE tree AS (
            SELECT l.id, l.title, l.postal_code, l.admin_level_id, l.parent_id,
                   ARRAY[l.id] AS path
            FROM location l WHERE l.parent_id IS NULL
            UNION ALL
            SELECT c.id, c.title, c.postal_code, c.admin_level_id, c.parent_id, c.id || t.path
            FROM location c JOIN tree t ON c.parent_id = t.id
            WHERE NOT c.id = ANY(t.path)
        )
        UPDATE location l SET
            full_location = CASE
                WHEN t.parent_id IS NULL OR t.admin_level_id IS NULL THEN
                    CASE WHEN :postal_code AND t.postal_code IS NOT NULL
                         THEN t.title || ' ' || t.postal_code ELSE t.title END
                ELSE (
                    SELECT string_agg(loc.title, ', ' ORDER BY la.display_order NULLS LAST)
                    FROM unnest(t.path) WITH ORDINALITY AS ids(id, ord)
                    JOIN location loc ON loc.id = ids.id
                    LEFT JOIN location_admin_level la ON loc.admin_level_id = la.id
                ) || CASE WHEN :postal_code AND t.postal_code IS NOT NULL
                          THEN ' ' || t.postal_code ELSE '' END
            END,
            id_tree = (
                SELECT string_agg('[' || ids.id || ']', ' ' ORDER BY ids.ord)
                FROM unnest(t.path) WITH ORDINALITY AS ids(id, ord)
            )
        FROM tree t WHERE l.id = t.id;
        """
        if not has_app_context():
            postal_code = False
        else:
            postal_code = current_app.config.get("LOCATIONS_INCLUDE_POSTAL_CODE", False)
        try:
            result = db.session.execute(text(query), {"postal_code": postal_code})
            db.session.commit()
            logger.info(f"Rebuilt location paths for {result.rowcount} locations.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to regenerate location strings: {str(e)}", exc_info=e)
            raise

    def rebuild_subtree(self) -> None:
        """
        Rebuild full_location and id_tree for this location and every descendant.

        Both columns are denormalized copies of the path from the root, so renaming
        a location or moving it invalidates every row underneath it, not just itself.
        Rebuilding only the edited row leaves descendants holding the old text and,
        worse, the old ancestor chain, which drops them out of ancestor search.
        """
        query = """
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
        subtree AS (
            SELECT l.id, l.title, l.postal_code, l.admin_level_id, l.parent_id,
                   (SELECT path FROM root_path) AS path
            FROM location l WHERE l.id = :id
            UNION ALL
            SELECT c.id, c.title, c.postal_code, c.admin_level_id, c.parent_id, c.id || s.path
            FROM location c JOIN subtree s ON c.parent_id = s.id
            -- a pre-existing cycle would otherwise recurse until the statement times out
            WHERE NOT c.id = ANY(s.path)
        )
        UPDATE location l SET
            full_location = CASE
                WHEN s.parent_id IS NULL OR s.admin_level_id IS NULL THEN
                    CASE WHEN :postal_code AND s.postal_code IS NOT NULL
                         THEN s.title || ' ' || s.postal_code ELSE s.title END
                ELSE (
                    SELECT string_agg(loc.title, ', ' ORDER BY la.display_order NULLS LAST)
                    FROM unnest(s.path) WITH ORDINALITY AS ids(id, ord)
                    JOIN location loc ON loc.id = ids.id
                    LEFT JOIN location_admin_level la ON loc.admin_level_id = la.id
                ) || CASE WHEN :postal_code AND s.postal_code IS NOT NULL
                          THEN ' ' || s.postal_code ELSE '' END
            END,
            id_tree = (
                SELECT string_agg('[' || ids.id || ']', ' ' ORDER BY ids.ord)
                FROM unnest(s.path) WITH ORDINALITY AS ids(id, ord)
            )
        FROM subtree s WHERE l.id = s.id;
        """
        if not has_app_context():
            postal_code = False
        else:
            postal_code = current_app.config.get("LOCATIONS_INCLUDE_POSTAL_CODE", False)
        try:
            db.session.execute(text(query), {"id": self.id, "postal_code": postal_code})
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to rebuild location subtree {self.id}: {str(e)}", exc_info=e)
            raise

    @staticmethod
    def count_stale_paths() -> int:
        """
        Locations whose stored full_location disagrees with the current titles.

        Anything writing rows outside the app (imports, scripts, psql) leaves the
        denormalized text behind. This makes that drift visible instead of silent.
        """
        query = """
        WITH RECURSIVE tree AS (
            SELECT id, title, postal_code, admin_level_id, parent_id, full_location, id_tree,
                   ARRAY[id] AS path
            FROM location WHERE parent_id IS NULL
            UNION ALL
            SELECT c.id, c.title, c.postal_code, c.admin_level_id, c.parent_id, c.full_location,
                   c.id_tree, c.id || t.path
            FROM location c JOIN tree t ON c.parent_id = t.id
            WHERE NOT c.id = ANY(t.path)
        ),
        expected AS (
            SELECT t.id, t.full_location, t.id_tree,
                CASE
                    WHEN t.parent_id IS NULL OR t.admin_level_id IS NULL THEN
                        CASE WHEN :postal_code AND t.postal_code IS NOT NULL
                             THEN t.title || ' ' || t.postal_code ELSE t.title END
                    ELSE (
                        SELECT string_agg(loc.title, ', ' ORDER BY la.display_order NULLS LAST)
                        FROM unnest(t.path) WITH ORDINALITY AS ids(id, ord)
                        JOIN location loc ON loc.id = ids.id
                        LEFT JOIN location_admin_level la ON loc.admin_level_id = la.id
                    ) || CASE WHEN :postal_code AND t.postal_code IS NOT NULL
                              THEN ' ' || t.postal_code ELSE '' END
                END AS expected_full,
                (
                    SELECT string_agg('[' || ids.id || ']', ' ' ORDER BY ids.ord)
                    FROM unnest(t.path) WITH ORDINALITY AS ids(id, ord)
                ) AS expected_tree
            FROM tree t
        )
        SELECT
            (SELECT count(*) FROM expected
              WHERE full_location IS DISTINCT FROM expected_full
                 OR id_tree IS DISTINCT FROM expected_tree)
            -- rows the walk never reached are unrooted or caught in a cycle, so
            -- their stored path cannot be correct either
          + (SELECT count(*) FROM location l
              WHERE NOT EXISTS (SELECT 1 FROM tree t WHERE t.id = l.id));
        """
        if not has_app_context():
            postal_code = False
        else:
            postal_code = current_app.config.get("LOCATIONS_INCLUDE_POSTAL_CODE", False)
        return db.session.execute(text(query), {"postal_code": postal_code}).scalar() or 0

    def get_id_tree(self) -> str:
        """Use common table expressions to generate the full tree of ids, this is very useful to reduce
        search complexity when using autocomplete locations."""
        query = """
        with recursive tree(id,depth) as (
        select id, title, parent_id from location where id = :id
        union all
        select p.id, p.title, p.parent_id from location p, tree t
        where p.id = t.parent_id
        )
        select * from tree;
        """
        with db.engine.connect() as connection:
            result = connection.execute(text(query), {"id": self.id})
            return " ".join(["[{}]".format(loc[0]) for loc in result])

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
