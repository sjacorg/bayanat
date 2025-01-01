import json
from datetime import datetime
from typing import Any, Optional

from flask_login import current_user
from sqlalchemy.dialects.postgresql import TSVECTOR

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger
from enferno.admin.models.Itoa import Itoa
from enferno.admin.models.Itob import Itob
from enferno.admin.models.tables import (
    incident_labels,
    incident_potential_violations,
    incident_claimed_violations,
    incident_locations,
    incident_events,
    incident_roles,
)

from enferno.admin.models.utils import check_roles

logger = get_logger()


class Incident(db.Model, BaseMixin):
    """
    SQL Alchemy model for incidents
    """

    COLOR = "#f4be39"

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(255), nullable=False)
    title_ar = db.Column(db.String(255))

    description = db.Column(db.Text)

    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.relationship(
        "User", backref="assigned_to_incidents", foreign_keys=[assigned_to_id]
    )

    first_peer_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    second_peer_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    first_peer_reviewer = db.relationship(
        "User", backref="first_rev_incidents", foreign_keys=[first_peer_reviewer_id]
    )
    second_peer_reviewer = db.relationship(
        "User", backref="second_rev_incidents", foreign_keys=[second_peer_reviewer_id]
    )

    labels = db.relationship(
        "Label",
        secondary=incident_labels,
        backref=db.backref("incidents", lazy="dynamic"),
    )

    potential_violations = db.relationship(
        "PotentialViolation",
        secondary=incident_potential_violations,
        backref=db.backref("incidents", lazy="dynamic"),
    )

    claimed_violations = db.relationship(
        "ClaimedViolation",
        secondary=incident_claimed_violations,
        backref=db.backref("incidents", lazy="dynamic"),
    )

    locations = db.relationship(
        "Location",
        secondary=incident_locations,
        backref=db.backref("incidents", lazy="dynamic"),
    )

    events = db.relationship(
        "Event",
        secondary=incident_events,
        backref=db.backref("incidents", lazy="dynamic"),
        order_by="Event.from_date",
    )

    roles = db.relationship(
        "Role", secondary=incident_roles, backref=db.backref("incidents", lazy="dynamic")
    )

    # Related Actors
    related_actors = db.relationship("Itoa", backref="incident", foreign_keys="Itoa.incident_id")

    # Related Bulletins
    related_bulletins = db.relationship("Itob", backref="incident", foreign_keys="Itob.incident_id")

    # Related Incidents
    # Incidents that this incident relate to ->
    incidents_to = db.relationship("Itoi", backref="incident_from", foreign_keys="Itoi.incident_id")

    # Incidents that relate to this <-
    incidents_from = db.relationship(
        "Itoi", backref="incident_to", foreign_keys="Itoi.related_incident_id"
    )

    status = db.Column(db.String(255))

    comments = db.Column(db.Text)
    # review fields
    review = db.Column(db.Text)
    review_action = db.Column(db.String)

    tsv = db.Column(TSVECTOR)

    search = db.Column(
        db.Text,
        db.Computed(
            """
            CAST(id AS TEXT) || ' ' ||
            COALESCE(title, '') || ' ' ||
            COALESCE(title_ar, '') || ' ' ||
            COALESCE(regexp_replace(regexp_replace(description, E'<.*?>', '', 'g'), E'&nbsp;', '', 'g'), '') || ' ' ||
            COALESCE(comments, '')
            """
        ),
    )

    __table_args__ = (
        db.Index(
            "ix_incident_search",
            "search",
            postgresql_using="gin",
            postgresql_ops={"search": "gin_trgm_ops"},
        ),
    )

    def related(self, include_self: bool = False) -> dict[str, Any]:
        """
        Return a dictionary of related objects.

        Args:
            - include_self: whether to include the object itself.

        Returns:
            - the dictionary of related objects.
        """
        output = {}
        output["bulletin"] = [r.bulletin.id for r in self.bulletin_relations]
        output["actor"] = [r.actor.id for r in self.actor_relations]
        output["incident"] = []
        for r in self.incident_relations:
            incident = r.incident_to if self.id == r.incident_id else r.incident_from
            output["incident"].append(incident.id)

        # Include the object's own ID if include_self is True
        if include_self:
            table_name = self.__tablename__
            output[table_name].append(self.id)
        return output

    # helper method to create a revision
    def create_revision(
        self, user_id: Optional[t.id] = None, created: Optional[datetime] = None
    ) -> None:
        """
        Create a revision of the incident.

        Args:
            - user_id: the user id.
            - created: the creation date.
        """
        from enferno.admin.models import IncidentHistory

        if not user_id:
            user_id = getattr(current_user, "id", 1)
        i = IncidentHistory(incident_id=self.id, data=self.to_dict(), user_id=user_id)
        if created:
            i.created_at = created
            i.updated_at = created
        i.save()

    # returns all related incidents
    @property
    def incident_relations(self):
        return self.incidents_to + self.incidents_from

    # returns all related bulletins
    @property
    def bulletin_relations(self):
        return self.related_bulletins

    # returns all related actors
    @property
    def actor_relations(self):
        return self.related_actors

    @property
    def actor_relations_dict(self):
        return [relation.to_dict() for relation in self.actor_relations]

    @property
    def bulletin_relations_dict(self):
        return [relation.to_dict() for relation in self.bulletin_relations]

    @property
    def incident_relations_dict(self):
        return [relation.to_dict(exclude=self) for relation in self.incident_relations]

    # populate model from json dict
    def from_json(self, json: dict[str, Any]) -> "Incident":
        """
        Populate the object from a json dictionary.

        Args:
            - json: the json dictionary.

        Returns:
            - the updated object.
        """
        from enferno.admin.models import (
            Label,
            Location,
            PotentialViolation,
            ClaimedViolation,
            Event,
            Actor,
            Bulletin,
        )

        if not self.id:
            db.session.add(self)

        self.title = json["title"] if "title" in json else None
        self.title_ar = json["title_ar"] if "title_ar" in json else None

        self.description = json["description"] if "description" in json else None

        # Labels
        if "labels" in json:
            ids = [label["id"] for label in json["labels"]]
            labels = Label.query.filter(Label.id.in_(ids)).all()
            self.labels = labels

        # Locations
        if "locations" in json:
            ids = [location["id"] for location in json["locations"]]
            locations = Location.query.filter(Location.id.in_(ids)).all()
            self.locations = locations

        # Potential Violations
        if "potential_violations" in json:
            ids = [pv["id"] for pv in json["potential_violations"]]
            potential_violations = PotentialViolation.query.filter(
                PotentialViolation.id.in_(ids)
            ).all()
            self.potential_violations = potential_violations

        # Claimed Violations
        if "claimed_violations" in json:
            ids = [cv["id"] for cv in json["claimed_violations"]]
            claimed_violations = ClaimedViolation.query.filter(ClaimedViolation.id.in_(ids)).all()
            self.claimed_violations = claimed_violations

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

        # Related Actors (actor_relations)
        if "actor_relations" in json and "check_ar" in json:
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
                if not (r.actor_id in rel_ids):
                    rel_actor = r.actor
                    r.delete()

                    # -revision related actor
                    rel_actor.create_revision()

        # Related Bulletins (bulletin_relations)
        if "bulletin_relations" in json and "check_br" in json:
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

                    # -revision related bulletin
                    rel_bulletin.create_revision()

        # Related Incidnets (incident_relations)
        if "incident_relations" in json and "check_ir" in json:
            # collect related incident ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["incident_relations"]:
                incident = Incident.query.get(relation["incident"]["id"])
                # Extra (check those incidents exit)

                if incident:
                    rel_ids.append(incident.id)
                    # this will update/create the relationship (will flush to db)
                    self.relate_incident(incident, relation=relation)

                # Find out removed relations and remove them
            # just loop existing relations and remove if the destination incident no in the related ids

            for r in self.incident_relations:
                # get related incident (in or out)
                rid = r.get_other_id(self.id)
                if not (rid in rel_ids):
                    r.delete()

                    # - revision related incident
                    Incident.query.get(rid).create_revision()

        if "comments" in json:
            self.comments = json["comments"]

        if "status" in json:
            self.status = json["status"]

        return self

    # Compact dict for relationships
    @check_roles
    def to_compact(self) -> dict[str, Any]:
        """Return a compact dictionary representation of the incident."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or None,
        }

    # Helper method to handle logic of relating incidents
    def relate_incident(
        self,
        incident: "Incident",
        relation: Optional[dict[str, Any]] = None,
        create_revision: bool = True,
    ) -> None:
        """
        Relate two incidents.

        Args:
            - incident: the incident to relate.
            - relation: the relation dictionary.
            - create_revision: whether to create a revision.
        """
        from enferno.admin.models import Itoi

        # if a new actor is being created, we must save it to get the id
        if not self.id:
            self.save()

        # Relationships are alwasy forced to go from the lower id to the bigger id (to prevent duplicates)
        # Enough to look up the relationship from the lower to the upper

        # reject self relation
        if self == incident:
            return

        existing_relation = Itoi.are_related(self.id, incident.id)
        if existing_relation:
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation (possible from or to the actor based on the id comparison)
            new_relation = Itoi.relate(self, incident)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # -revision related incident
            if create_revision:
                incident.create_revision()

    # Helper method to handle logic of relating actors
    def relate_actor(
        self,
        actor: "Actor",
        relation: Optional[dict[str, Any]] = None,
        create_revision: bool = True,
    ) -> None:
        """
        Relate an incident to an actor.

        Args:
            - actor: the actor to relate.
            - relation: the relation dictionary.
            - create_revision: whether to create a revision.
        """
        # if current incident is new, save it to get the id
        if not self.id:
            self.save()

        # query order : (actor_id, incident_id)
        existing_relation = Itoa.query.get((actor.id, self.id))

        if existing_relation:
            # Relationship exists :: Updating the attributes
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation
            new_relation = Itoa(incident_id=self.id, actor_id=actor.id)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # -revision related actor
            if create_revision:
                actor.create_revision()

    # Helper method to handle logic of relating bulletins
    def relate_bulletin(
        self,
        bulletin: "Bulletin",
        relation: Optional[dict[str, Any]] = None,
        create_revision: bool = True,
    ) -> None:
        """
        Relate an incident to a bulletin.

        Args:
            - bulletin: the bulletin to relate.
            - relation: the relation dictionary.
            - create_revision: whether to create a revision.
        """
        # if current incident is new, save it to get the id
        if not self.id:
            self.save()

        # query order : (incident_id,bulletin_id)
        existing_relation = Itob.query.get((self.id, bulletin.id))

        if existing_relation:
            # Relationship exists :: Updating the attributes
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation
            new_relation = Itob(incident_id=self.id, bulletin_id=bulletin.id)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # -revision related bulletin
            if create_revision:
                bulletin.create_revision()

    @check_roles
    def to_dict(self, mode: Optional[str] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the incident.

        Args:
            - mode: the serialization mode. "1" for minimal, "2" for compact, "3"
                    for skip relations, None for full. Default is None.

        Returns:
            - the dictionary representation of the incident.
        """
        # Try to detect a user session
        if current_user:
            if not current_user.can_access(self):
                return self.restricted_json()

        if mode == "1":
            return self.min_json()
        if mode == "2":
            return self.to_mode2()

        # Labels json
        labels_json = []
        if self.labels and len(self.labels):
            for label in self.labels:
                labels_json.append({"id": label.id, "title": label.title})

        # Locations json
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(location.to_compact())

        # potential violations json
        pv_json = []
        if self.potential_violations and len(self.potential_violations):
            for pv in self.potential_violations:
                pv_json.append({"id": pv.id, "title": pv.title})

        # claimed violations json
        cv_json = []
        if self.claimed_violations and len(self.claimed_violations):
            for cv in self.claimed_violations:
                cv_json.append({"id": cv.id, "title": cv.title})

        # Events json
        events_json = []
        if self.events and len(self.events):
            for event in self.events:
                events_json.append(event.to_dict())

        bulletin_relations_dict = []
        actor_relations_dict = []
        incident_relations_dict = []

        if str(mode) != "3":
            # lazy load if mode is 3
            for relation in self.bulletin_relations:
                bulletin_relations_dict.append(relation.to_dict())

            for relation in self.actor_relations:
                actor_relations_dict.append(relation.to_dict())

            for relation in self.incident_relations:
                incident_relations_dict.append(relation.to_dict(exclude=self))

        return {
            "class": self.__tablename__,
            "id": self.id,
            "title": self.title or None,
            "title_ar": self.title_ar or None,
            "description": self.description or None,
            # assigned to
            "assigned_to": self.assigned_to.to_compact() if self.assigned_to else None,
            # first peer reviewer
            "first_peer_reviewer": (
                self.first_peer_reviewer.to_compact() if self.first_peer_reviewer else None
            ),
            "labels": labels_json,
            "locations": locations_json,
            "potential_violations": pv_json,
            "claimed_violations": cv_json,
            "events": events_json,
            "actor_relations": actor_relations_dict,
            "bulletin_relations": bulletin_relations_dict,
            "incident_relations": incident_relations_dict,
            "comments": self.comments if self.comments else None,
            "status": self.status if self.status else None,
            "review": self.review if self.review else None,
            "review_action": self.review_action if self.review_action else None,
            "updated_at": DateHelper.serialize_datetime(self.get_modified_date()),
            "roles": [role.to_dict() for role in self.roles] if self.roles else [],
        }

    # custom serialization mode
    def to_mode2(self) -> dict[str, Any]:
        """Return a compact dictionary representation of the incident."""
        # Labels json
        labels_json = []
        if self.labels and len(self.labels):
            for label in self.labels:
                labels_json.append({"id": label.id, "title": label.title})

        # Locations json
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(location.min_json())

        return {
            "class": "Incident",
            "id": self.id,
            "title": self.title or None,
            "description": self.description or None,
            "labels": labels_json,
            "locations": locations_json,
            "comments": self.comments if self.comments else None,
            "status": self.status if self.status else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the incident."""
        return json.dumps(self.to_dict())

    def get_modified_date(self) -> datetime:
        """Return the last modified date of the incident."""
        if self.history:
            return self.history[-1].updated_at
        else:
            return self.updated_at


# ----------------------------------- History Tables (Versioning) ------------------------------------
