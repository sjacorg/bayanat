from typing import Any

from flask_babel import gettext
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.attributes import flag_modified

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import Source, Label
from enferno.admin.models.tables import actor_sources, actor_labels, actor_verlabels

logger = get_logger()


class ActorProfile(db.Model, BaseMixin):
    __tablename__ = "actor_profile"

    # Mode Constants
    MODE_PROFILE = 1
    MODE_MAIN = 2
    MODE_MISSING_PERSON = 3

    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(
        db.Integer, default=MODE_PROFILE, nullable=False
    )  # 1: profile , 2: main , 3: missing person
    originid = db.Column(db.String, index=True)
    description = db.Column(db.Text)
    source_link = db.Column(db.String(255))
    source_link_type = db.Column(db.Boolean, default=False)
    publish_date = db.Column(db.DateTime)
    documentation_date = db.Column(db.DateTime)

    search = db.Column(
        db.Text,
        db.Computed(
            """
         (id)::text || ' ' ||
         COALESCE(originid, ''::character varying) || ' ' ||
         COALESCE(description, ''::character varying) || ' ' ||
         COALESCE(source_link, ''::text)
        """
        ),
    )

    # Foreign key to reference the Actor
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"))

    # Relationship back to the Actor
    actor = db.relationship(
        "Actor", backref=db.backref("actor_profiles", lazy=True, order_by="ActorProfile.created_at")
    )

    # sources, labels, and verlabels relationships
    sources = db.relationship(
        "Source",
        secondary=actor_sources,
        backref=db.backref("actor_profiles", lazy="dynamic"),
    )
    labels = db.relationship(
        "Label",
        secondary=actor_labels,
        backref=db.backref("actor_profiles", lazy="dynamic"),
    )
    ver_labels = db.relationship(
        "Label",
        secondary=actor_verlabels,
        backref=db.backref("verlabels_actor_profiles", lazy="dynamic"),
    )

    last_address = db.Column(db.Text, comment="MP")
    social_networks = db.Column(JSONB, comment="MP")
    marriage_history = db.Column(db.String, comment="MP")
    pregnant_at_disappearance = db.Column(db.String, comment="MP")
    months_pregnant = db.Column(db.Integer, comment="MP")
    missing_relatives = db.Column(db.Boolean, comment="MP")
    saw_name = db.Column(db.String, comment="MP")
    saw_address = db.Column(db.Text, comment="MP")
    saw_email = db.Column(db.String, comment="MP")
    saw_phone = db.Column(db.String, comment="MP")
    detained_before = db.Column(db.String, comment="MP")
    seen_in_detention = db.Column(JSONB, comment="MP")
    injured = db.Column(JSONB, comment="MP")
    known_dead = db.Column(JSONB, comment="MP")
    death_details = db.Column(db.Text, comment="MP")
    personal_items = db.Column(db.Text, comment="MP")
    height = db.Column(db.Integer, comment="MP")
    weight = db.Column(db.Integer, comment="MP")
    physique = db.Column(db.String, comment="MP")
    hair_loss = db.Column(db.String, comment="MP")
    hair_type = db.Column(db.String, comment="MP")
    hair_length = db.Column(db.String, comment="MP")
    hair_color = db.Column(db.String, comment="MP")
    facial_hair = db.Column(db.String, comment="MP")
    posture = db.Column(db.Text, comment="MP")
    skin_markings = db.Column(JSONB, comment="MP")
    handedness = db.Column(db.String, comment="MP")
    glasses = db.Column(db.String, comment="MP")
    eye_color = db.Column(db.String, comment="MP")
    dist_char_con = db.Column(db.String, comment="MP")
    dist_char_acq = db.Column(db.String, comment="MP")
    physical_habits = db.Column(db.String, comment="MP")
    other = db.Column(db.Text, comment="MP")
    phys_name_contact = db.Column(db.Text, comment="MP")
    injuries = db.Column(db.Text, comment="MP")
    implants = db.Column(db.Text, comment="MP")
    malforms = db.Column(db.Text, comment="MP")
    pain = db.Column(db.Text, comment="MP")
    other_conditions = db.Column(db.Text, comment="MP")
    accidents = db.Column(db.Text, comment="MP")
    pres_drugs = db.Column(db.Text, comment="MP")
    smoker = db.Column(db.String, comment="MP")
    dental_record = db.Column(db.Boolean, comment="MP")
    dentist_info = db.Column(db.Text, comment="MP")
    teeth_features = db.Column(db.Text, comment="MP")
    dental_problems = db.Column(db.Text, comment="MP")
    dental_treatments = db.Column(db.Text, comment="MP")
    dental_habits = db.Column(db.Text, comment="MP")
    case_status = db.Column(db.String, comment="MP")
    # array of objects: name, email,phone, email, address, relationship
    reporters = db.Column(JSONB, comment="MP")
    identified_by = db.Column(db.String, comment="MP")
    family_notified = db.Column(db.Boolean, comment="MP")
    hypothesis_based = db.Column(db.Text, comment="MP")
    hypothesis_status = db.Column(db.String, comment="MP")
    # death_cause = db.Column(db.String)
    reburial_location = db.Column(db.String, comment="MP")

    __table_args__ = (
        db.Index(
            "ix_actor_profile_search",
            "search",
            postgresql_using="gin",
            postgresql_ops={"search": "gin_trgm_ops"},
        ),
    )

    def from_json(self, json: dict[str, Any]) -> "ActorProfile":
        """
        Populate the object from a json dictionary.

        Args:
            - json: the json dictionary.

        Returns:
            - the populated object.
        """
        from enferno.admin.models import Source, Label

        if not self.id:
            db.session.add(self)

        self.mode = json.get("mode", self.mode)
        self.originid = json["originid"] if "originid" in json else None
        self.description = json.get("description", self.description)
        self.source_link = json.get("source_link", self.source_link)
        self.source_link_type = json.get("source_link_type", self.source_link_type)
        self.publish_date = json.get("publish_date", self.publish_date)
        self.documentation_date = json.get("documentation_date", self.documentation_date)

        # Handling Sources
        if "sources" in json:
            source_ids = [source["id"] for source in json["sources"] if "id" in source]
            self.sources = (
                Source.query.filter(Source.id.in_(source_ids)).all() if source_ids else []
            )

        # Handling Labels
        if "labels" in json:
            label_ids = [label["id"] for label in json["labels"] if "id" in label]
            self.labels = Label.query.filter(Label.id.in_(label_ids)).all() if label_ids else []

        # Handling Verified Labels
        if "ver_labels" in json:
            ver_label_ids = [label["id"] for label in json["ver_labels"] if "id" in label]
            self.ver_labels = (
                Label.query.filter(Label.id.in_(ver_label_ids)).all() if ver_label_ids else []
            )

        if self.mode == 3:
            self.last_address = json.get("last_address")
            self.marriage_history = json.get("marriage_history")
            self.pregnant_at_disappearance = json.get("pregnant_at_disappearance")
            months_pregnant_value = json.get("months_pregnant")
            self.months_pregnant = int(months_pregnant_value) if months_pregnant_value else None
            self.missing_relatives = json.get("missing_relatives")
            self.saw_name = json.get("saw_name")
            self.saw_address = json.get("saw_address")
            self.saw_phone = json.get("saw_phone")
            self.saw_email = json.get("saw_email")
            self.seen_in_detention = json.get("seen_in_detention")
            # Flag json fields for saving
            flag_modified(self, "seen_in_detention")
            self.injured = json.get("injured")
            flag_modified(self, "injured")
            self.known_dead = json.get("known_dead")
            flag_modified(self, "known_dead")
            self.death_details = json.get("death_details")
            self.personal_items = json.get("personal_items")
            height_value = json.get("height")
            self.height = int(height_value) if height_value else None
            weight_value = json.get("weight")
            self.weight = int(weight_value) if weight_value else None
            self.physique = json.get("physique")
            self.hair_loss = json.get("hair_loss")
            self.hair_type = json.get("hair_type")
            self.hair_length = json.get("hair_length")
            self.hair_color = json.get("hair_color")
            self.facial_hair = json.get("facial_hair")
            self.posture = json.get("posture")
            self.skin_markings = json.get("skin_markings")
            flag_modified(self, "skin_markings")
            self.handedness = json.get("handedness")
            self.eye_color = json.get("eye_color")
            self.glasses = json.get("glasses")
            self.dist_char_con = json.get("dist_char_con")
            self.dist_char_acq = json.get("dist_char_acq")
            self.physical_habits = json.get("physical_habits")
            self.other = json.get("other")
            self.phys_name_contact = json.get("phys_name_contact")
            self.injuries = json.get("injuries")
            self.implants = json.get("implants")
            self.malforms = json.get("malforms")
            self.pain = json.get("pain")
            self.other_conditions = json.get("other_conditions")
            self.accidents = json.get("accidents")
            self.pres_drugs = json.get("pres_drugs")
            self.smoker = json.get("smoker")
            self.dental_record = json.get("dental_record")
            self.dentist_info = json.get("dentist_info")
            self.teeth_features = json.get("teeth_features")
            self.dental_problems = json.get("dental_problems")
            self.dental_treatments = json.get("dental_treatments")
            self.dental_habits = json.get("dental_habits")
            self.case_status = json.get("case_status")
            self.reporters = json.get("reporters")
            flag_modified(self, "reporters")
            self.identified_by = json.get("identified_by")
            self.family_notified = json.get("family_notified")
            self.reburial_location = json.get("reburial_location")
            self.hypothesis_based = json.get("hypothesis_based")
            self.hypothesis_status = json.get("hypothesis_status")

        return self

    def mp_json(self) -> dict[str, Any]:
        """Return a dictionary representation of the missing person fields."""
        mp = {}
        mp["MP"] = True
        mp["last_address"] = getattr(self, "last_address")
        mp["marriage_history"] = getattr(self, "marriage_history")
        mp["pregnant_at_disappearance"] = getattr(self, "pregnant_at_disappearance")
        mp["months_pregnant"] = str(self.months_pregnant) if self.months_pregnant else None
        mp["missing_relatives"] = getattr(self, "missing_relatives")
        mp["saw_name"] = getattr(self, "saw_name")
        mp["saw_address"] = getattr(self, "saw_address")
        mp["saw_phone"] = getattr(self, "saw_phone")
        mp["saw_email"] = getattr(self, "saw_email")
        mp["seen_in_detention"] = getattr(self, "seen_in_detention")
        mp["injured"] = getattr(self, "injured")
        mp["known_dead"] = getattr(self, "known_dead")
        mp["death_details"] = getattr(self, "death_details")
        mp["personal_items"] = getattr(self, "personal_items")
        mp["height"] = str(self.height) if self.height else None
        mp["weight"] = str(self.weight) if self.weight else None
        mp["physique"] = getattr(self, "physique")
        mp["_physique"] = getattr(self, "physique")

        mp["hair_loss"] = getattr(self, "hair_loss")
        mp["_hair_loss"] = gettext(self.hair_loss)

        mp["hair_type"] = getattr(self, "hair_type")
        mp["_hair_type"] = gettext(self.hair_type)

        mp["hair_length"] = getattr(self, "hair_length")
        mp["_hair_length"] = gettext(self.hair_length)

        mp["hair_color"] = getattr(self, "hair_color")
        mp["_hair_color"] = gettext(self.hair_color)

        mp["facial_hair"] = getattr(self, "facial_hair")
        mp["_facial_hair"] = gettext(self.facial_hair)

        mp["posture"] = getattr(self, "posture")
        mp["skin_markings"] = getattr(self, "skin_markings")
        if self.skin_markings and self.skin_markings.get("opts"):
            mp["_skin_markings"] = [gettext(item) for item in self.skin_markings["opts"]]

        mp["handedness"] = getattr(self, "handedness")
        mp["_handedness"] = gettext(self.handedness)
        mp["eye_color"] = getattr(self, "eye_color")
        mp["_eye_color"] = gettext(self.eye_color)

        mp["glasses"] = getattr(self, "glasses")
        mp["dist_char_con"] = getattr(self, "dist_char_con")
        mp["dist_char_acq"] = getattr(self, "dist_char_acq")
        mp["physical_habits"] = getattr(self, "physical_habits")
        mp["other"] = getattr(self, "other")
        mp["phys_name_contact"] = getattr(self, "phys_name_contact")
        mp["injuries"] = getattr(self, "injuries")
        mp["implants"] = getattr(self, "implants")
        mp["malforms"] = getattr(self, "malforms")
        mp["pain"] = getattr(self, "pain")
        mp["other_conditions"] = getattr(self, "other_conditions")
        mp["accidents"] = getattr(self, "accidents")
        mp["pres_drugs"] = getattr(self, "pres_drugs")
        mp["smoker"] = getattr(self, "smoker")
        mp["dental_record"] = getattr(self, "dental_record")
        mp["dentist_info"] = getattr(self, "dentist_info")
        mp["teeth_features"] = getattr(self, "teeth_features")
        mp["dental_problems"] = getattr(self, "dental_problems")
        mp["dental_treatments"] = getattr(self, "dental_treatments")
        mp["dental_habits"] = getattr(self, "dental_habits")
        mp["case_status"] = getattr(self, "case_status")
        mp["_case_status"] = gettext(self.case_status)
        mp["reporters"] = getattr(self, "reporters")
        mp["identified_by"] = getattr(self, "identified_by")
        mp["family_notified"] = getattr(self, "family_notified")
        mp["reburial_location"] = getattr(self, "reburial_location")
        mp["hypothesis_based"] = getattr(self, "hypothesis_based")
        mp["hypothesis_status"] = getattr(self, "hypothesis_status")
        return mp

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the actor profile."""
        actor_profile_dict = {
            "id": self.id,
            "mode": self.mode,
            "originid": self.originid or None,
            "description": self.description or None,
            "source_link": self.source_link or None,
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
            "actor_id": self.actor_id,
            "sources": self.serialize_relationship(self.sources),
            "labels": self.serialize_relationship(self.labels),
            "ver_labels": self.serialize_relationship(self.ver_labels),
        }

        # Include missing person fields if mode is MODE_MISSING_PERSON
        if self.mode == ActorProfile.MODE_MISSING_PERSON:
            mp_data = self.mp_json()
            actor_profile_dict.update(mp_data)

        return actor_profile_dict
