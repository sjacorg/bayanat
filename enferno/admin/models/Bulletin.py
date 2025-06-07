import json
from datetime import datetime
from typing import Any, Optional

import sqlalchemy
from flask_login import current_user
from geoalchemy2 import Geography
from sqlalchemy import ARRAY, func
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.csv_utils import convert_simple_relation, convert_complex_relation
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

from enferno.admin.models.Atob import Atob
from enferno.admin.models.Itob import Itob
from enferno.admin.models.Location import Location
from enferno.admin.models.GeoLocation import GeoLocation
from enferno.admin.models.Event import Event


from enferno.admin.models.tables import (
    bulletin_roles,
    bulletin_sources,
    bulletin_locations,
    bulletin_labels,
    bulletin_verlabels,
    bulletin_events,
)
from enferno.admin.models.utils import check_roles

logger = get_logger()


class Bulletin(db.Model, BaseMixin):
    """
    SQL Alchemy model for bulletins
    """

    COLOR = "#4a9bed"

    extend_existing = True

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))

    sjac_title = db.Column(db.String(255))
    sjac_title_ar = db.Column(db.String(255))

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_bulletins", foreign_keys=[user_id])

    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.relationship(
        "User", backref="assigned_to_bulletins", foreign_keys=[assigned_to_id]
    )
    description = db.Column(db.Text)

    reliability_score = db.Column(db.Integer, default=0)

    first_peer_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    second_peer_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    first_peer_reviewer = db.relationship(
        "User", backref="first_rev_bulletins", foreign_keys=[first_peer_reviewer_id]
    )
    second_peer_reviewer = db.relationship(
        "User", backref="second_rev_bulletins", foreign_keys=[second_peer_reviewer_id]
    )

    sources = db.relationship(
        "Source",
        secondary=bulletin_sources,
        backref=db.backref("bulletins", lazy="dynamic"),
    )
    locations = db.relationship(
        "Location",
        secondary=bulletin_locations,
        backref=db.backref("bulletins", lazy="dynamic"),
    )

    geo_locations = db.relationship(
        "GeoLocation",
        backref="bulletin",
    )

    labels = db.relationship(
        "Label",
        secondary=bulletin_labels,
        backref=db.backref("bulletins", lazy="dynamic"),
    )

    ver_labels = db.relationship(
        "Label",
        secondary=bulletin_verlabels,
        backref=db.backref("verlabels_bulletins", lazy="dynamic"),
    )

    events = db.relationship(
        "Event",
        secondary=bulletin_events,
        backref=db.backref("bulletins", lazy="dynamic"),
        order_by="Event.from_date",
    )

    roles = db.relationship(
        "Role", secondary=bulletin_roles, backref=db.backref("bulletins", lazy="dynamic")
    )

    # Bulletins that this bulletin relate to ->
    bulletins_to = db.relationship("Btob", backref="bulletin_from", foreign_keys="Btob.bulletin_id")

    # Bulletins that relate to this <-
    bulletins_from = db.relationship(
        "Btob", backref="bulletin_to", foreign_keys="Btob.related_bulletin_id"
    )

    # Related Actors
    related_actors = db.relationship("Atob", backref="bulletin", foreign_keys="Atob.bulletin_id")

    # Related Incidents
    related_incidents = db.relationship("Itob", backref="bulletin", foreign_keys="Itob.bulletin_id")

    publish_date = db.Column(db.DateTime, index=True)
    documentation_date = db.Column(db.DateTime, index=True)

    status = db.Column(db.String(255))
    source_link = db.Column(db.String(255))
    source_link_type = db.Column(db.Boolean, default=False)

    # tags field : used for etl tagging etc ..
    tags = db.Column(ARRAY(db.String), default=[], nullable=False)

    # extra fields used by etl etc ..
    originid = db.Column(db.String, index=True)
    comments = db.Column(db.Text)

    # review fields
    review = db.Column(db.Text)
    review_action = db.Column(db.String)

    # metadata
    meta = db.Column(JSONB)

    tsv = db.Column(TSVECTOR)

    search = db.Column(
        db.Text,
        db.Computed(
            """
            CAST(id AS TEXT) || ' ' ||
            COALESCE(title, '') || ' ' ||
            COALESCE(title_ar, '') || ' ' ||
            COALESCE(description, '') || ' ' ||
            COALESCE(originid, '') || ' ' ||
            COALESCE(sjac_title, '') || ' ' ||
            COALESCE(sjac_title_ar, '') || ' ' ||
            COALESCE(source_link, '') || ' ' ||
            COALESCE(comments, '')
            """
        ),
    )

    __table_args__ = (
        db.Index(
            "ix_bulletin_search",
            "search",
            postgresql_using="gin",
            postgresql_ops={"search": "gin_trgm_ops"},
        ),
    )

    # custom method to create new revision in history table
    def create_revision(
        self, user_id: Optional[t.id] = None, created: Optional[datetime] = None
    ) -> None:
        """
        Create a new revision in the history table.

        Args:
            - user_id: the id of the user.
            - created: the created date.
        """
        from enferno.admin.models import BulletinHistory

        if not user_id:
            user_id = getattr(current_user, "id", 1)
        b = BulletinHistory(bulletin_id=self.id, data=self.to_dict(), user_id=user_id)
        if created:
            b.created_at = created
            b.updated_at = created
        b.save()

    def related(self, include_self: bool = False) -> dict[str, Any]:
        """
        Get related objects.

        Args:
            - include_self: include self in output.

        Returns:
            - dictionary containing related objects ids by type.
        """
        output = {}
        output["actor"] = [r.actor.id for r in self.related_actors]
        output["incident"] = [r.incident.id for r in self.related_incidents]
        output["bulletin"] = []
        for r in self.bulletin_relations:
            bulletin = r.bulletin_to if self.id == r.bulletin_id else r.bulletin_from
            output["bulletin"].append(bulletin.id)
        if include_self:
            table_name = self.__tablename__
            output[table_name].append(self.id)
        return output

    # helper property returns all bulletin relations
    @property
    def bulletin_relations(self) -> list["Btob"]:
        """Return all bulletin relations."""
        return self.bulletins_to + self.bulletins_from

    @property
    def bulletin_relations_dict(self) -> list[dict[str, Any]]:
        """Return a list of dictionary representations of the bulletin relations."""
        return [relation.to_dict(exclude=self) for relation in self.bulletin_relations]

    @property
    def actor_relations_dict(self) -> list[dict[str, Any]]:
        """Return a list of dictionary representations of the actor relations."""
        return [relation.to_dict() for relation in self.actor_relations]

    @property
    def incident_relations_dict(self) -> list[dict[str, Any]]:
        """Return a list of dictionary representations of the incident relations."""
        return [relation.to_dict() for relation in self.incident_relations]

    # helper property returns all actor relations
    @property
    def actor_relations(self) -> list["Atob"]:
        """Return all actor relations."""
        return self.related_actors

    # helper property returns all incident relations
    @property
    def incident_relations(self) -> list["Itob"]:
        """Return all incident relations."""
        return self.related_incidents

    # populate object from json dict
    def from_json(self, json: dict[str, Any]) -> "Bulletin":
        """
        Populate the object from a json dictionary.

        Args:
            - json: the json dictionary.

        Returns:
            - the populated object.
        """
        from enferno.admin.models import (
            Location,
            Source,
            Label,
            GeoLocation,
            Event,
            Media,
            Actor,
            Incident,
        )

        if not self.id:
            db.session.add(self)

        self.originid = json["originid"] if "originid" in json else None
        self.title = json["title"] if "title" in json else None
        self.sjac_title = json["sjac_title"] if "sjac_title" in json else None

        self.title_ar = json["title_ar"] if "title_ar" in json else None
        self.sjac_title_ar = json["sjac_title_ar"] if "sjac_title_ar" in json else None

        # assigned to
        if "assigned_to" in json:
            if json["assigned_to"]:
                if "id" in json["assigned_to"]:
                    self.assigned_to_id = json["assigned_to"]["id"]

        # first_peer_reviewer
        if "first_peer_reviewer" in json:
            if json["first_peer_reviewer"]:
                if "id" in json["first_peer_reviewer"]:
                    self.first_peer_reviewer_id = json["first_peer_reviewer"]["id"]

        self.description = json["description"] if "description" in json else None
        self.comments = json["comments"] if "comments" in json else None
        self.source_link = json["source_link"] if "source_link" in json else None
        self.source_link_type = json.get("source_link_type", False)
        self.tags = json["tags"] if "tags" in json else []

        # Locations
        if "locations" in json:
            ids = [location["id"] for location in json["locations"]]
            locations = Location.query.filter(Location.id.in_(ids)).all()
            self.locations = locations

        # geo_locations = json.get('geoLocations')
        if "geoLocations" in json:
            geo_locations = json["geoLocations"]
            final_locations = []
            for geo in geo_locations:
                if id not in geo:
                    # new geolocation
                    g = GeoLocation()
                    g.from_json(geo)
                    g.save()
                else:
                    # geolocation exists // update
                    g = GeoLocation.query.get(geo["id"])
                    g.from_json(geo)
                    g.save()
                final_locations.append(g)
            self.geo_locations = final_locations

        # Sources
        if "sources" in json:
            ids = [source["id"] for source in json["sources"]]
            sources = Source.query.filter(Source.id.in_(ids)).all()
            self.sources = sources

        # Labels
        if "labels" in json:
            ids = [label["id"] for label in json["labels"]]
            labels = Label.query.filter(Label.id.in_(ids)).all()
            self.labels = labels

        # verified Labels
        if "verLabels" in json:
            ids = [label["id"] for label in json["verLabels"]]
            ver_labels = Label.query.filter(Label.id.in_(ids)).all()
            self.ver_labels = ver_labels

        # Events
        if "events" in json:
            new_events = []
            events = json["events"]

            for event in events:
                if "id" not in event:
                    # new event
                    e = Event()
                    e = e.from_json(event)
                    e.save()
                else:
                    # event already exists, get a db instnace and update it with new data
                    e = Event.query.get(event["id"])
                    e.from_json(event)
                    e.save()
                new_events.append(e)
            self.events = new_events

        # Related Media
        if "medias" in json:
            # untouchable main medias
            main = [m for m in self.medias if m.main is True]
            others = [m for m in self.medias if not m.main]
            to_keep_ids = [m.get("id") for m in json.get("medias") if m.get("id")]

            # handle removed medias
            to_be_deleted = [m for m in others if m.id not in to_keep_ids]

            others = [m for m in others if m.id in to_keep_ids]
            to_be_created = [m for m in json.get("medias") if not m.get("id")]

            new_medias = []
            # create new medias
            for media in to_be_created:
                m = Media()
                m = m.from_json(media)
                m.save()
                new_medias.append(m)

            self.medias = main + others + new_medias

            # mark removed media as deleted
            for media in to_be_deleted:
                media.deleted = True
                delete_comment = f"Removed from Bulletin #{self.id}"
                media.comments = (
                    media.comments + "\n" + delete_comment if media.comments else delete_comment
                )
                media.save()

        # Related Bulletins (bulletin_relations)
        if "bulletin_relations" in json:
            # collect related bulletin ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["bulletin_relations"]:
                bulletin = Bulletin.query.get(relation["bulletin"]["id"])
                # Extra (check those bulletins exit)

                if bulletin:
                    rel_ids.append(bulletin.id)
                    # this will update/create the relationship (will flush to db)
                    self.relate_bulletin(bulletin, relation=relation)

                # Find out removed relations and remove them
            # just loop existing relations and remove if the destination bulletin no in the related ids

            for r in self.bulletin_relations:
                # get related bulletin (in or out)
                rid = r.get_other_id(self.id)
                if not (rid in rel_ids):
                    r.delete()

                    # ------- create revision on the other side of the relationship
                    Bulletin.query.get(rid).create_revision()

        # Related Actors (actors_relations)
        if "actor_relations" in json:
            # collect related bulletin ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["actor_relations"]:
                actor = Actor.query.get(relation["actor"]["id"])
                if actor:
                    rel_ids.append(actor.id)
                    # helper method to update/create the relationship (will flush to db)
                    self.relate_actor(actor, relation=relation)

            # Find out removed relations and remove them
            # just loop existing relations and remove if the destination actor no in the related ids

            for r in self.actor_relations:
                # get related bulletin (in or out)
                if not (r.actor_id in rel_ids):
                    rel_actor = r.actor
                    r.delete()

                    # --revision relation
                    rel_actor.create_revision()

        # Related Incidents (incidents_relations)
        if "incident_relations" in json:
            # collect related incident ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["incident_relations"]:
                incident = Incident.query.get(relation["incident"]["id"])
                if incident:
                    rel_ids.append(incident.id)
                    # helper method to update/create the relationship (will flush to db)
                    self.relate_incident(incident, relation=relation)

            # Find out removed relations and remove them
            # just loop existing relations and remove if the destination incident no in the related ids

            for r in self.incident_relations:
                # get related bulletin (in or out)
                if not (r.incident_id in rel_ids):
                    rel_incident = r.incident
                    r.delete()

                    # --revision relation
                    rel_incident.create_revision()

        self.publish_date = json.get("publish_date", None)
        if self.publish_date == "":
            self.publish_date = None
        self.documentation_date = json.get("documentation_date", None)
        if self.documentation_date == "":
            self.documentation_date = None
        if "comments" in json:
            self.comments = json["comments"]

        if "status" in json:
            self.status = json["status"]

        return self

    # Compact dict for relationships
    @check_roles
    def to_compact(self) -> dict[str, Any]:
        """Return a compact dictionary representation of the bulletin."""
        # locations json
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(location.to_compact())

        # sources json
        sources_json = []
        if self.sources and len(self.sources):
            for source in self.sources:
                sources_json.append({"id": source.id, "title": source.title})

        return {
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar,
            "sjac_title": self.sjac_title or None,
            "sjac_title_ar": self.sjac_title_ar or None,
            "originid": self.originid or None,
            "locations": locations_json,
            "sources": sources_json,
            "description": self.description or None,
            "source_link": self.source_link or None,
            "source_link_type": getattr(self, "source_link_type", False),
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
            "comments": self.comments or "",
        }

    def to_csv_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the bulletin for csv export."""

        from enferno.admin.models import Actor, Incident

        output = {
            "id": self.id,
            "title": self.serialize_column("title"),
            "title_ar": self.serialize_column("title_ar"),
            "origin_id": self.serialize_column("originid"),
            "source_link": self.serialize_column("source_link"),
            "sjac_title": self.serialize_column("sjac_title"),
            "sjac_title_ar": self.serialize_column("sjac_title_ar"),
            "description": self.serialize_column("description"),
            "publish_date": self.serialize_column("publish_date"),
            "documentation_date": self.serialize_column("documentation_date"),
            "labels": convert_simple_relation(self.labels),
            "verified_labels": convert_simple_relation(self.ver_labels),
            "sources": convert_simple_relation(self.sources),
            "locations": convert_simple_relation(self.locations),
            "geo_locations": convert_simple_relation(self.geo_locations),
            "media": convert_simple_relation(self.medias),
            "events": convert_simple_relation(self.events),
            "related_bulletins": convert_complex_relation(
                self.bulletin_relations_dict, Bulletin.__tablename__
            ),
            "related_actors": convert_complex_relation(
                self.actor_relations_dict, Actor.__tablename__
            ),
            "related_incidents": convert_complex_relation(
                self.incident_relations_dict, Incident.__tablename__
            ),
        }
        return output

    # Helper method to handle logic of relating bulletins  (from bulletin)
    def relate_bulletin(
        self, bulletin: "Bulletin", relation: Optional[dict] = None, create_revision: bool = True
    ) -> None:
        from enferno.admin.models import Btob

        """
        Relate two bulletins.

        Args:
            - bulletin: the bulletin to relate to.
            - relation: the relation data.
            - create_revision: create a revision.
        """
        # if a new bulletin is being created, we must save it to get the id
        if not self.id:
            self.save()

        # Relationships are alwasy forced to go from the lower id to the bigger id (to prevent duplicates)
        # Enough to look up the relationship from the lower to the upper

        # reject self relation
        if self == bulletin:
            # Cant relate bulletin to itself
            return

        existing_relation = Btob.are_related(self.id, bulletin.id)

        if existing_relation:
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation (possible from or to the bulletin based on the id comparison)
            new_relation = Btob.relate(self, bulletin)

            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # ------- create revision on the other side of the relationship
            if create_revision:
                bulletin.create_revision()

    # Helper method to handle logic of relating incidents (from a bulletin)

    def relate_incident(
        self, incident: "Incident", relation: Optional[dict] = None, create_revision: bool = True
    ):
        """
        Relate a bulletin to an incident.

        Args:
            - incident: the incident to relate to.
            - relation: the relation data.
            - create_revision: create a revision.
        """
        # if current bulletin is new, save it to get the id
        if not self.id:
            self.save()

        # query order : (incident_id,bulletin_id)
        existing_relation = Itob.query.get((incident.id, self.id))

        if existing_relation:
            # Relationship exists :: Updating the attributes
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation
            new_relation = Itob(incident_id=incident.id, bulletin_id=self.id)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # --revision relation
            if create_revision:
                incident.create_revision()

    # helper method to relate actors
    def relate_actor(
        self, actor: "Actor", relation: Optional[dict] = None, create_revision: bool = True
    ) -> None:
        """
        Relate a bulletin to an actor.

        Args:
            - actor: the actor to relate to.
            - relation: the relation data.
            - create_revision: create a revision.
        """
        # if current bulletin is new, save it to get the id
        if not self.id:
            self.save()

        # query order : (bulletin_id,actor_id)
        existing_relation = Atob.query.get((self.id, actor.id))

        if existing_relation:
            # Relationship exists :: Updating the attributes
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation
            new_relation = Atob(bulletin_id=self.id, actor_id=actor.id)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # --revision relation
            if create_revision:
                actor.create_revision()

    # custom serialization method
    @check_roles
    def to_dict(self, mode: Optional[str] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the bulletin.

        Args:
            - mode: the serialization mode. "1" for minimal, "2" for compact, "3" to skip relations,
            None for full. Defaults to None.

        Returns:
            - the dictionary representation of the bulletin.
        """
        if mode == "2":
            return self.to_mode2()
        if mode == "1":
            return self.min_json()

        # Get base dictionary with dynamic fields
        data = super().to_dict()

        # locations json
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(location.to_compact())

        # locations json
        geo_locations_json = []
        if self.geo_locations:
            for geo in self.geo_locations:
                geo_locations_json.append(geo.to_dict())

        # sources json
        sources_json = []
        if self.sources and len(self.sources):
            for source in self.sources:
                sources_json.append({"id": source.id, "title": source.title})

        # labels json
        labels_json = []
        if self.labels and len(self.labels):
            for label in self.labels:
                labels_json.append({"id": label.id, "title": label.title})

        # verified labels json
        ver_labels_json = []
        if self.ver_labels and len(self.ver_labels):
            for vlabel in self.ver_labels:
                ver_labels_json.append({"id": vlabel.id, "title": vlabel.title})

        # events json
        events_json = []
        if self.events and len(self.events):
            for event in self.events:
                events_json.append(event.to_dict())

        # medias json
        medias_json = []
        if self.medias and len(self.medias):
            for media in self.medias:
                medias_json.append(media.to_dict())

        # Related bulletins json (actually the associated relationships)
        # - in this case the other bulletin carries the relationship
        bulletin_relations_dict = []
        actor_relations_dict = []
        incident_relations_dict = []

        if str(mode) != "3":
            for relation in self.bulletin_relations:
                bulletin_relations_dict.append(relation.to_dict(exclude=self))

            # Related actors json (actually the associated relationships)
            for relation in self.actor_relations:
                actor_relations_dict.append(relation.to_dict())

            # Related incidents json (actually the associated relationships)
            for relation in self.incident_relations:
                incident_relations_dict.append(relation.to_dict())

        # Update with bulletin-specific fields
        data.update(
            {
                "class": self.__tablename__,
                "id": self.id,
                "title": self.title,
                "title_ar": self.title_ar,
                "sjac_title": self.sjac_title or None,
                "sjac_title_ar": self.sjac_title_ar or None,
                "originid": self.originid or None,
                # assigned to
                "assigned_to": self.assigned_to.to_compact() if self.assigned_to else None,
                # first peer reviewer
                "first_peer_reviewer": (
                    self.first_peer_reviewer.to_compact() if self.first_peer_reviewer_id else None
                ),
                "locations": locations_json,
                "geoLocations": geo_locations_json,
                "labels": labels_json,
                "verLabels": ver_labels_json,
                "sources": sources_json,
                "events": events_json,
                "medias": medias_json,
                "bulletin_relations": bulletin_relations_dict,
                "actor_relations": actor_relations_dict,
                "incident_relations": incident_relations_dict,
                "description": self.description or None,
                "comments": self.comments or None,
                "source_link": self.source_link or None,
                "source_link_type": self.source_link_type or None,
                "tags": self.tags or [],
                "publish_date": DateHelper.serialize_datetime(self.publish_date),
                "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
                "status": self.status,
                "review": self.review if self.review else None,
                "review_action": self.review_action if self.review_action else None,
                "updated_at": DateHelper.serialize_datetime(self.get_modified_date()),
                "roles": [role.to_dict() for role in self.roles] if self.roles else [],
            }
        )

        return data

    # custom serialization mode
    def to_mode2(self) -> dict[str, Any]:
        """Return a compact dictionary representation of the bulletin."""
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(location.to_compact())

        # sources json
        sources_json = []
        if self.sources and len(self.sources):
            for source in self.sources:
                sources_json.append({"id": source.id, "title": source.title})

        return {
            "class": "Bulletin",
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar,
            "sjac_title": self.sjac_title or None,
            "sjac_title_ar": self.sjac_title_ar or None,
            "originid": self.originid or None,
            # assigned to
            "locations": locations_json,
            "sources": sources_json,
            "description": self.description or None,
            "comments": self.comments or None,
            "source_link": self.source_link or None,
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
        }

    def to_json(self) -> str:
        """Return a json representation of the bulletin."""
        return json.dumps(self.to_dict())

    @staticmethod
    def get_columns() -> list[str]:
        """Return the columns of the bulletin table."""
        columns = []
        for column in Bulletin.__table__.columns:
            columns.append(column.name)
        return columns

    @staticmethod
    def geo_query_location(
        target_point: dict[str, float], radius_in_meters: int
    ) -> sqlalchemy.sql.elements.BinaryExpression:
        """
        Geosearch via locations.

        Args:
            - target_point: the target point dict with 'lat' and 'lng' keys.
            - radius_in_meters: the radius in meters.

        Returns:
            - the query.
        """
        point = func.ST_SetSRID(
            func.ST_MakePoint(target_point.get("lng"), target_point.get("lat")), 4326
        )
        return Bulletin.id.in_(
            db.session.query(bulletin_locations.c.bulletin_id)
            .join(Location, bulletin_locations.c.location_id == Location.id)
            .filter(
                func.ST_DWithin(
                    func.cast(Location.latlng, Geography),
                    func.cast(point, Geography),
                    radius_in_meters,
                )
            )
        )

    @staticmethod
    def geo_query_geo_location(
        target_point: dict[str, float], radius_in_meters: int
    ) -> sqlalchemy.sql.elements.BinaryExpression:
        """
        Geosearch via geolocations.

        Args:
            - target_point: the target point dict with 'lat' and 'lng' keys.
            - radius_in_meters: the radius in meters.

        Returns:
            - the query.
        """
        point = func.ST_SetSRID(
            func.ST_MakePoint(target_point.get("lng"), target_point.get("lat")), 4326
        )
        return Bulletin.id.in_(
            db.session.query(GeoLocation.bulletin_id).filter(
                func.ST_DWithin(
                    func.cast(GeoLocation.latlng, Geography),
                    func.cast(point, Geography),
                    radius_in_meters,
                )
            )
        )

    @staticmethod
    def geo_query_event_location(
        target_point: dict[str, float], radius_in_meters: int
    ) -> sqlalchemy.sql.elements.BinaryExpression:
        """
        Condition for association between bulletin and location via events.

        Args:
            - target_point: the target point dict with 'lat' and 'lng' keys.
            - radius_in_meters: the radius in meters.

        Returns:
            - the query.
        """
        point = func.ST_SetSRID(
            func.ST_MakePoint(target_point.get("lng"), target_point.get("lat")), 4326
        )

        return Bulletin.id.in_(
            db.session.query(bulletin_events.c.bulletin_id)
            .join(Event, bulletin_events.c.event_id == Event.id)
            .join(Location, Event.location_id == Location.id)
            .filter(
                func.ST_DWithin(
                    func.cast(Location.latlng, Geography),
                    func.cast(point, Geography),
                    radius_in_meters,
                )
            )
        )

    def get_modified_date(self) -> datetime:
        """Return the modified date of the bulletin."""
        if self.history:
            return self.history[-1].updated_at
        else:
            return self.updated_at
