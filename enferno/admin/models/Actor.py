import json
from datetime import datetime
from typing import Any, Optional

import sqlalchemy
from flask_babel import gettext
from flask_login import current_user
from geoalchemy2 import Geography
from sqlalchemy import ARRAY, func, event, DDL
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
from sqlalchemy.sql import text

import enferno.utils.typing as t
from enferno.admin.models.Dialect import Dialect
from enferno.admin.models.Event import Event


from enferno.admin.models.Atob import Atob
from enferno.admin.models.Itoa import Itoa
from enferno.admin.models.Location import Location

from enferno.admin.models.IDNumberType import IDNumberType

from enferno.admin.models.tables import (
    actor_roles,
    actor_events,
)
from enferno.admin.models.Country import Country
from enferno.admin.models.Ethnography import Ethnography
from enferno.admin.models.utils import check_roles
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.csv_utils import convert_simple_relation, convert_complex_relation
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Actor(db.Model, BaseMixin):
    """
    SQL Alchemy model for actors
    """

    COLOR = "#74daa3"

    extend_existing = True

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255))
    name_ar = db.Column(db.String(255))

    nickname = db.Column(db.String(255))
    nickname_ar = db.Column(db.String(255))

    first_name = db.Column(db.String(255))
    first_name_ar = db.Column(db.String(255))

    middle_name = db.Column(db.String(255))
    middle_name_ar = db.Column(db.String(255))

    last_name = db.Column(db.String(255))
    last_name_ar = db.Column(db.String(255))

    father_name = db.Column(db.String(255))
    father_name_ar = db.Column(db.String(255))

    mother_name = db.Column(db.String(255))
    mother_name_ar = db.Column(db.String(255))

    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.relationship(
        "User", backref="assigned_to_actors", foreign_keys=[assigned_to_id]
    )

    first_peer_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    second_peer_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    first_peer_reviewer = db.relationship(
        "User", backref="first_rev_actors", foreign_keys=[first_peer_reviewer_id]
    )
    second_peer_reviewer = db.relationship(
        "User", backref="second_rev_actors", foreign_keys=[second_peer_reviewer_id]
    )

    roles = db.relationship(
        "Role", secondary=actor_roles, backref=db.backref("actors", lazy="dynamic")
    )

    events = db.relationship(
        "Event",
        secondary=actor_events,
        backref=db.backref("actors", lazy="dynamic"),
        order_by="Event.from_date",
    )

    # Actors that this actor relate to ->
    actors_to = db.relationship("Atoa", backref="actor_from", foreign_keys="Atoa.actor_id")

    # Actors that relate to this <-
    actors_from = db.relationship("Atoa", backref="actor_to", foreign_keys="Atoa.related_actor_id")

    # Related Bulletins
    related_bulletins = db.relationship("Atob", backref="actor", foreign_keys="Atob.actor_id")

    # Related Incidents
    related_incidents = db.relationship("Itoa", backref="actor", foreign_keys="Itoa.actor_id")

    type = db.Column(db.String(255))
    sex = db.Column(db.String(255))
    age = db.Column(db.String(255))
    civilian = db.Column(db.String(255))

    origin_place_id = db.Column(db.Integer, db.ForeignKey("location.id"))
    origin_place = db.relationship(
        "Location", backref="actors_origin_place", foreign_keys=[origin_place_id]
    )

    occupation = db.Column(db.String(255))
    occupation_ar = db.Column(db.String(255))

    position = db.Column(db.String(255))
    position_ar = db.Column(db.String(255))

    family_status = db.Column(db.String(255))
    no_children = db.Column(db.Integer)

    ethnographies = db.relationship(
        "Ethnography", secondary="actor_ethnographies", backref=db.backref("actors", lazy="dynamic")
    )

    nationalities = db.relationship(
        "Country", secondary="actor_countries", backref=db.backref("actors", lazy="dynamic")
    )

    dialects = db.relationship(
        "Dialect", secondary="actor_dialects", backref=db.backref("actors", lazy="dynamic")
    )

    id_number = db.Column(JSONB, default=[], nullable=False)

    status = db.Column(db.String(255))

    comments = db.Column(db.Text)
    # review fields
    review = db.Column(db.Text)
    review_action = db.Column(db.String)

    # tags field : used for etl tagging etc ..
    tags = db.Column(ARRAY(db.String), default=[], nullable=False)

    # metadata
    meta = db.Column(JSONB)

    tsv = db.Column(TSVECTOR)

    search = db.Column(
        db.Text,
        db.Computed(
            """
         (id)::text || ' ' ||
         COALESCE(name, ''::character varying) || ' ' ||
         COALESCE(name_ar, ''::character varying) || ' ' ||
         COALESCE(comments, ''::text)
        """
        ),
    )

    __table_args__ = (
        db.Index(
            "ix_actor_search",
            "search",
            postgresql_using="gin",
            postgresql_ops={"search": "gin_trgm_ops"},
        ),
        db.Index(
            "ix_actor_tags",
            "tags",
            postgresql_using="gin",
            postgresql_ops={"tags": "array_ops"},
        ),
        db.Index(
            "ix_actor_id_number_gin",
            "id_number",
            postgresql_using="gin",
        ),
        db.CheckConstraint("name IS NOT NULL OR name_ar IS NOT NULL", name="check_name"),
        db.CheckConstraint(
            "jsonb_typeof(id_number) = 'array'", name="check_actor_id_number_is_array"
        ),
        db.CheckConstraint(
            "validate_actor_id_number(id_number)", name="check_actor_id_number_element_structure"
        ),
    )

    # helper property to make all entities consistent
    @property
    def title(self):
        return self.name

    def related(self, include_self: bool = False) -> dict[str, Any]:
        """
        Return a dictionary of related entities.

        Args:
            - include_self: whether to include the current entity.

        Returns:
            - the dictionary of related entities.
        """
        output = {}
        output["bulletin"] = [r.bulletin.id for r in self.bulletin_relations]
        output["actor"] = []
        for r in self.actor_relations:
            actor = r.actor_to if self.id == r.actor_id else r.actor_from
            output["actor"].append(actor.id)
        output["incident"] = [r.incident.id for r in self.incident_relations]

        if include_self:
            table_name = self.__tablename__
            output[table_name].append(self.id)
        return output

    # helper method to create a revision
    def create_revision(
        self, user_id: Optional[t.id] = None, created: Optional[datetime] = None
    ) -> None:
        """
        Create a revision for the actor.

        Args:
            - user_id: the user id.
            - created: the created date.
        """
        from enferno.admin.models import ActorHistory

        if not user_id:
            user_id = getattr(current_user, "id", 1)

        a = ActorHistory(actor_id=self.id, data=self.to_dict(), user_id=user_id)
        if created:
            a.created_at = created
            a.updated_at = created
        a.save()

    # returns all related actors
    @property
    def actor_relations(self):
        return self.actors_to + self.actors_from

    # returns all related bulletins
    @property
    def bulletin_relations(self):
        return self.related_bulletins

    # returns all related incidents
    @property
    def incident_relations(self):
        return self.related_incidents

    @property
    def actor_relations_dict(self):
        return [relation.to_dict(exclude=self) for relation in self.actor_relations]

    @property
    def bulletin_relations_dict(self):
        return [relation.to_dict() for relation in self.bulletin_relations]

    @property
    def incident_relations_dict(self):
        return [relation.to_dict() for relation in self.incident_relations]

    @property
    def sources(self):
        """Return unique sources across all actor profiles."""
        return [
            source.to_dict()
            for source in set(
                source for profile in self.actor_profiles for source in profile.sources
            )
        ]

    @property
    def labels(self):
        return list(set(label for profile in self.actor_profiles for label in profile.labels))

    @property
    def verlabels(self):
        return list(
            set(ver_label for profile in self.actor_profiles for ver_label in profile.ver_labels)
        )

    @staticmethod
    def gen_full_name(first_name: str, last_name: str, middle_name: Optional[str] = None) -> str:
        name = first_name
        if middle_name:
            name = name + " " + middle_name
        name = name + " " + last_name
        return name

    # populate actor object from json dict
    def from_json(self, json: dict[str, Any]) -> "Actor":
        """
        Populate the actor object from a json dictionary.

        Args:
            - json: the json dictionary.

        Returns:
            - the populated object.
        """
        from enferno.admin.models import Media, Event, ActorProfile, Bulletin, Incident

        if not self.id:
            db.session.add(self)
        # All text fields

        self.type = json["type"] if "type" in json else None
        self.tags = json["tags"] if "tags" in json else []

        if self.type == "Entity":
            self.name = json["name"] if "name" in json else ""
            self.name_ar = json["name_ar"] if "name_ar" in json else ""

        elif self.type == "Person":
            self.first_name = (
                json["first_name"] if "first_name" in json and json["first_name"] else ""
            )
            self.first_name_ar = (
                json["first_name_ar"] if "first_name_ar" in json and json["first_name_ar"] else ""
            )

            self.middle_name = (
                json["middle_name"] if "middle_name" in json and json["middle_name"] else ""
            )
            self.middle_name_ar = (
                json["middle_name_ar"]
                if "middle_name_ar" in json and json["middle_name_ar"]
                else ""
            )

            self.last_name = json["last_name"] if "last_name" in json and json["last_name"] else ""
            self.last_name_ar = (
                json["last_name_ar"] if "last_name_ar" in json and json["last_name_ar"] else ""
            )

            self.name = self.gen_full_name(self.first_name, self.last_name, self.middle_name)
            self.name_ar = self.gen_full_name(
                self.first_name_ar, self.last_name_ar, self.middle_name_ar
            )

            self.father_name = json["father_name"] if "father_name" in json else ""
            self.father_name_ar = json["father_name_ar"] if "father_name_ar" in json else ""

            self.mother_name = json["mother_name"] if "mother_name" in json else ""
            self.mother_name_ar = json["mother_name_ar"] if "mother_name_ar" in json else ""

            self.sex = json["sex"] if "sex" in json else None
            self.age = json["age"] if "age" in json else None
            self.civilian = json["civilian"] if "civilian" in json else None

            self.occupation = json["occupation"] if "occupation" in json else None
            self.occupation_ar = json["occupation_ar"] if "occupation_ar" in json else None
            self.position = json["position"] if "position" in json else None
            self.position_ar = json["position_ar"] if "position_ar" in json else None

            self.family_status = json["family_status"] if "family_status" in json else None

            if "no_children" in json:
                try:
                    self.no_children = int(json["no_children"])
                except:
                    self.no_children = None

            # Ethnographies
            if "ethnographies" in json:
                ids = [ethnography.get("id") for ethnography in json["ethnographies"]]
                ethnographies = Ethnography.query.filter(Ethnography.id.in_(ids)).all()
                self.ethnographies = ethnographies

            # Nationalitites
            if "nationalities" in json:
                ids = [country.get("id") for country in json["nationalities"]]
                countries = Country.query.filter(Country.id.in_(ids)).all()
                self.nationalities = countries

            # Dialects
            if "dialects" in json:
                ids = [dialect.get("id") for dialect in json["dialects"]]
                dialects = Dialect.query.filter(Dialect.id.in_(ids)).all()
                self.dialects = dialects

        self.nickname = json["nickname"] if "nickname" in json else None
        self.nickname_ar = json["nickname_ar"] if "nickname_ar" in json else None

        # Handle id_number array format
        if "id_number" in json:
            if isinstance(json["id_number"], list):
                # Already in the correct format (list of objects)
                self.id_number = json["id_number"]
            elif isinstance(json["id_number"], str) and json["id_number"].strip():
                # Legacy string format - convert to array with default type (1)
                self.id_number = [{"type": "1", "number": json["id_number"]}]
            else:
                # Empty or null value
                self.id_number = []
        else:
            self.id_number = []

        if "origin_place" in json and json["origin_place"] and "id" in json["origin_place"]:
            self.origin_place_id = json["origin_place"]["id"]
        else:
            self.origin_place_id = None

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
                    # event already exists, get a db instance and update it with new data
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
                delete_comment = f"Removed from Actor #{self.id}"
                media.comments = (
                    media.comments + "\n" + delete_comment if media.comments else delete_comment
                )
                media.save()

        # Related Actors (actor_relations)
        if "actor_relations" in json:
            # collect related actors ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["actor_relations"]:
                actor = Actor.query.get(relation["actor"]["id"])

                # Extra (check those actors exit)

                if actor:
                    rel_ids.append(actor.id)
                    # this will update/create the relationship (will flush to db!)
                    self.relate_actor(actor, relation=relation)

                # Find out removed relations and remove them
            # just loop existing relations and remove if the destination actor not in the related ids

            for r in self.actor_relations:
                # get related actor (in or out)
                rid = r.get_other_id(self.id)
                if not (rid in rel_ids):
                    r.delete()

                    # -revision related
                    Actor.query.get(rid).create_revision()

        # Related Bulletins (bulletin_relations)
        if "bulletin_relations" in json:
            # collect related bulletin ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["bulletin_relations"]:
                bulletin = Bulletin.query.get(relation["bulletin"]["id"])

                # Extra (check those bulletins exit)
                if bulletin:
                    rel_ids.append(bulletin.id)
                    # this will update/create the relationship (will flush to db!)
                    self.relate_bulletin(bulletin, relation=relation)

            # Find out removed relations and remove them
            # just loop existing relations and remove if the destination bulletin not in the related ids
            for r in self.bulletin_relations:
                if not (r.bulletin_id in rel_ids):
                    rel_bulletin = r.bulletin
                    r.delete()

                    # -revision related
                    rel_bulletin.create_revision()

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

                    # -revision related incident
                    rel_incident.create_revision()

        if "comments" in json:
            self.comments = json["comments"]

        if "status" in json:
            self.status = json["status"]

        # Handling Actor Profiles
        if "actor_profiles" in json:
            existing_profile_ids = [profile.id for profile in self.actor_profiles]
            new_profile_data = json["actor_profiles"]

            # Update existing profiles or create new ones
            for profile_data in new_profile_data:
                if "id" in profile_data and profile_data["id"] in existing_profile_ids:
                    # Update existing profile
                    profile = next(
                        (p for p in self.actor_profiles if p.id == profile_data["id"]), None
                    )
                    if profile:
                        profile.from_json(profile_data)
                else:
                    # Create new profile
                    new_profile = ActorProfile()
                    new_profile = new_profile.from_json(profile_data)
                    new_profile.actor = self
                    self.actor_profiles.append(new_profile)

            # Remove profiles that are no longer associated
            for existing_id in existing_profile_ids:
                if existing_id not in [p.get("id") for p in new_profile_data]:
                    profile_to_remove = next(
                        (p for p in self.actor_profiles if p.id == existing_id), None
                    )
                    if profile_to_remove:
                        self.actor_profiles.remove(profile_to_remove)

        return self

    # Compact dict for relationships
    @check_roles
    def to_compact(self) -> dict[str, Any]:
        """Return a compact dictionary representation of the actor."""
        return {"id": self.id, "name": self.name, "sources": self.sources}

    def to_csv_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the actor for CSV export."""
        from enferno.admin.models.Bulletin import Bulletin
        from enferno.admin.models.Incident import Incident

        output = {
            "id": self.id,
            "name": self.serialize_column("name"),
            "name_ar": self.serialize_column("name_ar"),
            "nickname": self.serialize_column("nickname"),
            "nickname_ar": self.serialize_column("nickname_ar"),
            "middle_name": self.serialize_column("middle_name"),
            "middle_name_ar": self.serialize_column("middle_name_ar"),
            "last_name": self.serialize_column("last_name"),
            "last_name_ar": self.serialize_column("last_name_ar"),
            "mother_name": self.serialize_column("mother_name"),
            "mother_name_ar": self.serialize_column("mother_name_ar"),
            "sex": self.serialize_column("sex"),
            "age": self.serialize_column("age"),
            "civilian": self.serialize_column("civilian"),
            "type": self.serialize_column("type"),
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
        if self.id_number:
            output.update(self.flatten_id_numbers())
        return output

    def get_modified_date(self) -> datetime:
        """Return the last modified date of the actor."""
        if self.history:
            return self.history[-1].updated_at
        else:
            return self.updated_at

    # Helper method to handle logic of relating actors (from actor)

    def relate_actor(
        self,
        actor: "Actor",
        relation: Optional[dict[str, Any]] = None,
        create_revision: bool = True,
    ) -> None:
        """
        Relate the actor to another actor.

        Args:
            - actor: the actor to relate to.
            - relation: the relation dictionary.
            - create_revision: whether to create a revision.
        """
        from enferno.admin.models import Atoa

        # if a new actor is being created, we must save it to get the id
        if not self.id:
            self.save()

        # Relationships are alwasy forced to go from the lower id to the bigger id (to prevent duplicates)
        # Enough to look up the relationship from the lower to the upper

        # reject self relation
        if self == actor:
            # Cant relate bulletin to itself
            return

        existing_relation = Atoa.are_related(self.id, actor.id)
        if existing_relation:
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation (possible from or to the actor based on the id comparison)
            new_relation = Atoa.relate(self, actor)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # revision for related actor
            if create_revision:
                actor.create_revision()

    # Helper method to handle logic of relating bulletin (from am actor)
    def relate_bulletin(
        self,
        bulletin: "Bulletin",
        relation: Optional[dict[str, Any]] = None,
        create_revision: bool = True,
    ) -> None:
        """
        Relate the actor to a bulletin.

        Args:
            - bulletin: the bulletin to relate to.
            - relation: the relation dictionary.
            - create_revision: whether to create a revision.
        """
        # if current actor is new, save it to get the id
        if not self.id:
            self.save()

        # query order : (bulletin_id,actor_id)
        existing_relation = Atob.query.get((bulletin.id, self.id))

        if existing_relation:
            # Relationship exists :: Updating the attributes
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation
            new_relation = Atob(bulletin_id=bulletin.id, actor_id=self.id)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # revision for related bulletin
            if create_revision:
                bulletin.create_revision()

    # Helper method to handle logic of relating incidents (from an actor)
    def relate_incident(
        self,
        incident: "Incident",
        relation: Optional[dict[str, Any]] = None,
        create_revision: bool = True,
    ) -> None:
        """
        Relate the actor to an incident.

        Args:
            - incident: the incident to relate to.
            - relation: the relation dictionary.
            - create_revision: whether to create a revision.
        """
        # if current bulletin is new, save it to get the id
        if not self.id:
            self.save()

        # query order : (actor_id,incident_id)
        existing_relation = Itoa.query.get((self.id, incident.id))

        if existing_relation:
            # Relationship exists :: Updating the attributes
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation
            new_relation = Itoa(actor_id=self.id, incident_id=incident.id)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # revision for related incident
            if create_revision:
                incident.create_revision()

    @check_roles
    def to_dict(self, mode: Optional[str] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the actor.

        Args:
            - mode: the mode of serialization. "1" for minimal, "2" for mode2, "3" for skip relations,
                    and None for full serialization.

        Returns:
            - the dictionary representation of the actor.
        """
        if mode == "1":
            return self.min_json()
        if mode == "2":
            return self.to_mode2()

        # Events json
        events_json = []
        if self.events and len(self.events):
            for event in self.events:
                events_json.append(event.to_dict())

        # medias json
        medias_json = []
        if self.medias and len(self.medias):
            for media in self.medias:
                medias_json.append(media.to_dict())

        bulletin_relations_dict = []
        actor_relations_dict = []
        incident_relations_dict = []

        if str(mode) != "3":
            # lazy load if mode is 3
            for relation in self.bulletin_relations:
                bulletin_relations_dict.append(relation.to_dict())

            for relation in self.actor_relations:
                actor_relations_dict.append(relation.to_dict(exclude=self))

            for relation in self.incident_relations:
                incident_relations_dict.append(relation.to_dict())

        actor = {
            "class": self.__tablename__,
            "id": self.id,
            "name": self.name or None,
            "name_ar": getattr(self, "name_ar"),
            "nickname": self.nickname or None,
            "nickname_ar": getattr(self, "nickname_ar"),
            "first_name": self.first_name or None,
            "first_name_ar": self.first_name_ar or None,
            "middle_name": self.middle_name or None,
            "middle_name_ar": self.middle_name_ar or None,
            "last_name": self.last_name or None,
            "last_name_ar": self.last_name_ar or None,
            "father_name": self.father_name or None,
            "father_name_ar": self.father_name_ar or None,
            "mother_name": self.mother_name or None,
            "mother_name_ar": self.mother_name_ar or None,
            "sex": self.sex,
            "_sex": gettext(self.sex),
            "age": self.age,
            "_age": gettext(self.age),
            "civilian": self.civilian or None,
            "_civilian": gettext(self.civilian),
            "type": self.type,
            "_type": gettext(self.type),
            "occupation": self.occupation or None,
            "occupation_ar": self.occupation_ar or None,
            "position": self.position or None,
            "position_ar": self.position_ar or None,
            "family_status": self.family_status or None,
            "no_children": self.no_children or None,
            "ethnographies": [
                ethnography.to_dict() for ethnography in getattr(self, "ethnographies", [])
            ],
            "nationalities": [country.to_dict() for country in getattr(self, "nationalities", [])],
            "dialects": [dialect.to_dict() for dialect in getattr(self, "dialects", [])],
            "id_number": self.id_number or [],
            # assigned to
            "assigned_to": self.assigned_to.to_compact() if self.assigned_to else None,
            # first peer reviewer
            "first_peer_reviewer": (
                self.first_peer_reviewer.to_compact() if self.first_peer_reviewer else None
            ),
            "comments": self.comments or None,
            "events": events_json,
            "medias": medias_json,
            "actor_relations": actor_relations_dict,
            "bulletin_relations": bulletin_relations_dict,
            "incident_relations": incident_relations_dict,
            "origin_place": self.origin_place.to_dict() if self.origin_place else None,
            "tags": self.tags or [],
            "status": self.status,
            "review": self.review if self.review else None,
            "review_action": self.review_action if self.review_action else None,
            "updated_at": DateHelper.serialize_datetime(self.get_modified_date()),
            "roles": [role.to_dict() for role in self.roles] if self.roles else [],
            "actor_profiles": [profile.to_dict() for profile in self.actor_profiles],
        }

        return actor

    def to_mode2(self) -> dict[str, Any]:
        """Return a dictionary representation of the actor in mode 2."""
        return {
            "class": "Actor",
            "id": self.id,
            "type": self.type or None,
            "name": self.name or None,
            "comments": self.comments or None,
            "status": self.status or None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the actor."""
        return json.dumps(self.to_dict())

    @staticmethod
    def geo_query_origin_place(
        target_point: dict[str, float], radius_in_meters: int
    ) -> sqlalchemy.sql.elements.BinaryExpression:
        """
        Condition for direct association between actor and origin_place.

        Args:
            - target_point: the target point.
            - radius_in_meters: the radius in meters.

        Returns:
            - the query.
        """
        point = func.ST_SetSRID(
            func.ST_MakePoint(target_point.get("lng"), target_point.get("lat")), 4326
        )
        return Actor.id.in_(
            db.session.query(Actor.id)
            .join(Location, Actor.origin_place_id == Location.id)
            .filter(
                func.ST_DWithin(
                    func.cast(Location.latlng, Geography),
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
        Condition for association between actor and location via events.

        Args:
            - target_point: the target point.
            - radius_in_meters: the radius in meters.

        Returns:
            - the query.
        """
        point = func.ST_SetSRID(
            func.ST_MakePoint(target_point.get("lng"), target_point.get("lat")), 4326
        )
        return Actor.id.in_(
            db.session.query(actor_events.c.actor_id)
            .join(Event, actor_events.c.event_id == Event.id)
            .join(Location, Event.location_id == Location.id)
            .filter(
                func.ST_DWithin(
                    func.cast(Location.latlng, Geography),
                    func.cast(point, Geography),
                    radius_in_meters,
                )
            )
        )

    def validate(self) -> bool:
        """
        a helper method to validate actors upon setting values from CSV row, invalid actors can be dropped.
        :return:
        """
        if not self.name:
            return False
        return True

    def flatten_profiles(self) -> dict[str, Any]:
        """
        Return a flattened dictionary representation of the actor's profiles.
        Each profile's fields are prefixed with 'profile_X_' where X is the profile number.

        Returns:
            dict: Flattened dictionary of all profile data
        """
        # Define base fields that exist for all profile modes
        base_fields = [
            "mode",
            "originid",
            "description",
            "source_link",
            "source_link_type",
            "publish_date",
            "documentation_date",
        ]

        # Define additional fields for mode 3 (Missing Person)
        mode_3_fields = [
            "last_address",
            "marriage_history",
            "pregnant_at_disappearance",
            "months_pregnant",
            "missing_relatives",
            "saw_name",
            "saw_address",
            "saw_email",
            "saw_phone",
            "seen_in_detention",
            "injured",
            "known_dead",
            "death_details",
            "personal_items",
            "height",
            "weight",
            "physique",
            "hair_loss",
            "hair_type",
            "hair_length",
            "hair_color",
            "facial_hair",
            "posture",
            "skin_markings",
            "handedness",
            "glasses",
            "eye_color",
            "dist_char_con",
            "dist_char_acq",
            "physical_habits",
            "other",
            "phys_name_contact",
            "injuries",
            "implants",
            "malforms",
            "pain",
            "other_conditions",
            "accidents",
            "pres_drugs",
            "smoker",
            "dental_record",
            "dentist_info",
            "teeth_features",
            "dental_problems",
            "dental_treatments",
            "dental_habits",
            "case_status",
            "reporters",
            "identified_by",
            "family_notified",
            "hypothesis_based",
            "hypothesis_status",
            "reburial_location",
        ]

        flattened = {}

        for idx, profile in enumerate(self.actor_profiles, 1):
            prefix = f"profile_{idx}_"

            # Handle base fields using dict comprehension
            flattened.update({f"{prefix}{field}": getattr(profile, field) for field in base_fields})

            # Handle relationships that need custom processing
            flattened[f"{prefix}sources"] = (
                [s.title for s in profile.sources] if profile.sources else []
            )
            flattened[f"{prefix}labels"] = (
                [l.title for l in profile.labels] if profile.labels else []
            )
            flattened[f"{prefix}ver_labels"] = (
                [l.title for l in profile.ver_labels] if profile.ver_labels else []
            )

            # Handle mode 3 specific fields if applicable
            if profile.mode == 3:
                flattened.update(
                    {f"{prefix}{field}": getattr(profile, field) for field in mode_3_fields}
                )

        return flattened

    def flatten_id_numbers(self) -> dict[str, Any]:
        """
        Return a flattened dictionary representation of the actor's id numbers.
        For each id number, the type's name is retrieved and used as a key.
        If multiple id numbers of the same type are present, each one is suffixed with an `_X` where X is a number starting from 1.
        """
        flattened = {}

        if not self.id_number:
            return flattened

        # Group id numbers by type to handle duplicates
        type_counts = {}
        type_titles = {}  # Cache for type titles

        for id_entry in self.id_number:
            if not isinstance(id_entry, dict) or "type" not in id_entry or "number" not in id_entry:
                continue

            type_id = id_entry["type"]
            number = id_entry["number"]

            # Get the IDNumberType title (cache it to avoid multiple DB queries)
            if type_id not in type_titles:
                try:
                    id_type = IDNumberType.query.get(int(type_id))
                    type_titles[type_id] = id_type.title if id_type else f"Unknown_Type_{type_id}"
                except (ValueError, TypeError):
                    type_titles[type_id] = f"Invalid_Type_{type_id}"

            title = type_titles[type_id]

            # Track how many times we've seen this type
            if title not in type_counts:
                type_counts[title] = 0
                flattened[title] = number
            else:
                type_counts[title] += 1
                flattened[f"{title}_{type_counts[title]}"] = number

        return flattened


# DDL event to create the validation function for fresh installs
create_validation_function = DDL(
    """
CREATE OR REPLACE FUNCTION validate_actor_id_number(id_number_data JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if it's an empty array (always valid)
    IF jsonb_array_length(id_number_data) = 0 THEN
        RETURN TRUE;
    END IF;
    
    -- Check each element has the required structure
    RETURN (
        SELECT bool_and(
            jsonb_typeof(elem->'type') = 'string' AND 
            jsonb_typeof(elem->'number') = 'string' AND
            (elem->'type') IS NOT NULL AND 
            (elem->'number') IS NOT NULL
        )
        FROM jsonb_array_elements(id_number_data) AS elem
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""
)

drop_validation_function = DDL(
    """
DROP FUNCTION IF EXISTS validate_actor_id_number(JSONB);
"""
)

# Register DDL events to ensure function exists for both fresh installs and migrations
event.listen(Actor.__table__, "before_create", create_validation_function)
event.listen(Actor.__table__, "before_drop", drop_validation_function)
