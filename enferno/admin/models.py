import json
import pathlib
from datetime import datetime
from functools import wraps
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Optional, Union

import pandas as pd
from dateutil.parser import parse
from flask import has_app_context, has_request_context
from flask_babel import gettext
from flask_login import current_user
from geoalchemy2 import Geometry, Geography
from geoalchemy2.shape import to_shape
from sqlalchemy import JSON, ARRAY, text, and_, or_, func
import sqlalchemy
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
from sqlalchemy.orm.attributes import flag_modified
import werkzeug
from werkzeug.utils import secure_filename

from enferno.extensions import db
from enferno.settings import Config as cfg
from enferno.utils.base import BaseMixin, ComponentDataMixin
from enferno.utils.csv_utils import convert_simple_relation, convert_complex_relation
from enferno.utils.date_helper import DateHelper
from enferno.user.models import User

from enferno.utils.logging_utils import get_logger
import enferno.utils.typing as t

logger = get_logger()


######  Role based Access Control Decorator for Bulletins / Actors  / Incidents  ######
def check_roles(method):
    """
    Decorator to check if the current user has access to the resource. If the
    user does not have access, the restricted_json method is called to return
    a restricted response.
    """

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        method_output = method(self, *method_args, **method_kwargs)
        if current_user:
            if not current_user.can_access(self):
                return self.restricted_json()
        return method_output

    return _impl


def check_relation_roles(method):
    """
    Decorator to check if the current user has access to the related resource.
    If the user does not have access, the restricted_json method is called to
    return a restricted related item in response.
    """

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        method_output = method(self, *method_args, **method_kwargs)
        bulletin = method_output.get("bulletin")
        if bulletin and bulletin.get("restricted"):
            return {"bulletin": bulletin, "restricted": True}

        actor = method_output.get("actor")
        if actor and actor.get("restricted"):
            return {"actor": actor, "restricted": True}

        incident = method_output.get("incident")
        if incident and incident.get("restricted"):
            return {"incident": incident, "restricted": True}
        return method_output

    return _impl


def check_history_access(method):
    """
    Decorator to check if the current user has access to the fulll history. If the
    user does not have the correct access, the to_dict method will return a shorter
    data histroy.
    """

    def can_access():
        if has_request_context() and has_app_context():
            return True if current_user.view_full_history else False
        return True

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        return method(self, full=can_access(), *method_args, **method_kwargs)

    return _impl


######  -----  ######


class Source(db.Model, BaseMixin):
    """
    SQL Alchemy model for sources
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    etl_id = db.Column(db.String, unique=True)
    title = db.Column(db.String, index=True)
    title_ar = db.Column(db.String, index=True)
    source_type = db.Column(db.String)
    comments = db.Column(db.Text)
    comments_ar = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey("source.id"), index=True)
    parent = db.relationship("Source", remote_side=id, backref="sub_source")

    def from_json(self, json: dict[str, Any]) -> "Source":
        self.title = json["title"]
        if "title_ar" in json:
            self.title_ar = json["title_ar"]
        if "comments" in json:
            self.comments = json["comments"]
        if "comments_ar" in json:
            self.comments = json["comments_ar"]
        parent = json.get("parent")
        if parent:
            self.parent_id = parent.get("id")
        else:
            self.parent_id = None
        return self

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the source."""
        return {
            "id": self.id,
            "title": self.title,
            "etl_id": self.etl_id,
            "parent": {"id": self.parent.id, "title": self.parent.title} if self.parent else None,
            "comments": self.comments,
            "updated_at": DateHelper.serialize_datetime(self.updated_at)
            if self.updated_at
            else None,
        }

    def __repr__(self) -> str:
        return "<Source {} {}>".format(self.id, self.title)

    def to_json(self) -> str:
        """Return a JSON representation of the source."""
        return json.dumps(self.to_dict())

    @staticmethod
    def find_by_ids(ids: list[t.id]) -> list[dict[str, Any]]:
        """
        finds all items and subitems of a given list of ids, using raw sql query instead of the orm.

        Args:
            - ids: list of ids to search for.

        Returns:
            - matching records
        """
        if not ids:
            return []
        qstr = tuple(ids)
        query = """
               with  recursive lcte (id, parent_id, title) as (
               select id, parent_id, title from source where id in :qstr union all 
               select x.id, x.parent_id, x.title from lcte c, source x where x.parent_id = c.id)
               select * from lcte;
               """
        result = db.engine.execute(text(query), qstr=qstr)

        return [{"id": x[0], "title": x[2]} for x in result]

    @staticmethod
    def get_children(sources: list, depth: int = 3) -> list:
        """
        Retrieves the children of the given sources up to a specified depth.

        Args:
            - sources: list of sources to retrieve children for.
            - depth: the depth of the search.

        Returns:
            - list of children sources.
        """
        all = []
        targets = sources
        while depth != 0:
            children = Source.get_direct_children(targets)
            all += children
            targets = children
            depth -= 1
        return all

    @staticmethod
    def get_direct_children(sources: list) -> list:
        """
        Retrieves the direct children of the given sources.

        Args:
            - sources: list of sources to retrieve children for.

        Returns:
            - list of children sources.
        """
        children = []
        for source in sources:
            children += source.sub_source
        return children

    @staticmethod
    def find_by_title(title: str) -> Optional["Source"]:
        """
        Finds a source by its title.

        Args:
            - title: the title of the source.

        Returns:
            - the source object.
        """
        ar = Source.query.filter(Source.title_ar.ilike(title)).first()
        if ar:
            return ar
        else:
            return Source.query.filter(Source.title.ilike(title)).first()

    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Imports Source data from a CSV file.

        Args:
            - file_storage: the file storage object containing the CSV data.

        Returns:
            - empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.comments = df.comments.fillna("")
        db.session.bulk_insert_mappings(Source, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from source").scalar()
        db.session.execute("alter sequence source_id_seq restart with :m", {"m": max_id})
        db.session.commit()

        return ""


class Label(db.Model, BaseMixin):
    """
    SQL Alchemy model for labels
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, index=True)
    title_ar = db.Column(db.String, index=True)
    comments = db.Column(db.String)
    comments_ar = db.Column(db.String)
    order = db.Column(db.Integer)
    verified = db.Column(db.Boolean, default=False)
    for_bulletin = db.Column(db.Boolean, default=False)
    for_actor = db.Column(db.Boolean, default=False)
    for_incident = db.Column(db.Boolean, default=False)
    for_offline = db.Column(db.Boolean, default=False)

    parent_label_id = db.Column(db.Integer, db.ForeignKey("label.id"), index=True, nullable=True)
    parent = db.relationship("Label", remote_side=id, backref="sub_label")

    # custom serialization method
    def to_dict(self, mode: str = "1") -> dict[str, Any]:
        """
        Return a dictionary representation of the label.

        Args:
            - mode: the serialization mode. Default is "1". If "2" is passed, a compact
            representation of the label is returned.

        Returns:
            - dictionary representation of the label.
        """
        if mode == "2":
            return self.to_mode2()
        return {
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar if self.title_ar else None,
            "comments": self.comments if self.comments else None,
            "comments_ar": self.comments_ar if self.comments_ar else None,
            "order": self.order,
            "verified": self.verified,
            "for_bulletin": self.for_bulletin,
            "for_actor": self.for_actor,
            "for_incident": self.for_incident,
            "for_offline": self.for_offline,
            "parent": {"id": self.parent.id, "title": self.parent.title} if self.parent else None,
            "updated_at": DateHelper.serialize_datetime(self.updated_at)
            if self.updated_at
            else None,
        }

    # custom compact serialization
    def to_mode2(self) -> dict[str, Any]:
        """
        Compact serialization for labels

        Returns:
            - dictionary with id and title keys.
        """
        return {
            "id": self.id,
            "title": self.title,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the label."""
        return json.dumps(self.to_dict())

    def __repr__(self) -> str:
        return "<Label {} {}>".format(self.id, self.title)

    @staticmethod
    def find_by_ids(ids: list[t.id]) -> list[dict[str, Any]]:
        """
        finds all items and subitems of a given list of ids, using raw sql query instead of the orm.

        Args:
            - ids: list of ids to search for.

        Returns:
            - matching records
        """
        if not ids:
            return []
        qstr = tuple(ids)

        query = """
                  with  recursive lcte (id, parent_label_id, title) as (
                  select id, parent_label_id, title from label where id in :qstr union all 
                  select x.id, x.parent_label_id, x.title from lcte c, label x where x.parent_label_id = c.id)
                  select * from lcte;
                  """
        result = db.engine.execute(text(query), qstr=qstr)

        return [{"id": x[0], "title": x[2]} for x in result]

    @staticmethod
    def get_children(labels: list, depth: int = 3) -> list:
        """
        Get the children of the given labels up to a specified depth.

        Args:
            - labels: list of labels to retrieve children for.
            - depth: the depth of the search.

        Returns:
            - list of children labels.
        """
        all = []
        targets = labels
        while depth != 0:
            children = Label.get_direct_children(targets)
            all += children
            targets = children
            depth -= 1
        return all

    @staticmethod
    def get_direct_children(labels: list) -> list:
        """
        Get the direct children of the given labels.

        Args:
            - labels: list of labels to retrieve children for.

        Returns:
            - list of children labels.
        """
        children = []
        for label in labels:
            children += label.sub_label
        return children

    @staticmethod
    def find_by_title(title: str) -> Optional["Label"]:
        """
        Find a label by its title.

        Args:
            - title: the title of the label.

        Returns:
            - the label object.
        """
        ar = Label.query.filter(Label.title_ar.ilike(title)).first()
        if ar:
            return ar
        else:
            return Label.query.filter(Label.title.ilike(title)).first()

    # populate object from json data
    def from_json(self, json: dict[str, Any]) -> "Label":
        """
        Create a label object from a json dictionary.

        Args:
            - json: the json dictionary to create the label from.

        Returns:
            - the label object.
        """
        self.title = json["title"]
        self.title_ar = json["title_ar"] if "title_ar" in json else ""
        self.comments = json["comments"] if "comments" in json else ""
        self.comments_ar = json["comments_ar"] if "comments_ar" in json else ""
        self.verified = json.get("verified", False)
        self.for_bulletin = json.get("for_bulletin", False)
        self.for_actor = json.get("for_actor", False)
        self.for_incident = json.get("for_incident", False)
        self.for_offline = json.get("for_offline", False)

        parent_info = json.get("parent")
        if parent_info and "id" in parent_info:
            parent_id = parent_info["id"]
            if parent_id != self.id:
                p_label = Label.query.get(parent_id)
                # Check for circular relations
                if (
                    p_label
                    and p_label.id != self.id
                    and (not p_label.parent or p_label.parent.id != self.id)
                ):
                    self.parent_label_id = p_label.id
                else:
                    self.parent_label_id = None
            else:
                self.parent_label_id = None
        else:
            self.parent_label_id = None

        return self

    # import csv data into db
    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Imports Label data from a CSV file.

        Args:
            - file_storage: the file storage object containing the CSV data.

        Returns:
            - empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.order.astype(int)

        # first ignore foreign key constraints
        dfi = df.copy()
        del dfi["parent_label_id"]

        # first insert
        db.session.bulk_insert_mappings(Label, dfi.to_dict(orient="records"))

        # then drop labels with no foreign keys and update
        df = df[df["parent_label_id"].notna()]
        db.session.bulk_update_mappings(Label, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from label").scalar()
        db.session.execute("alter sequence label_id_seq restart with :m", {"m": max_id})
        db.session.commit()
        return ""


class Eventtype(db.Model, BaseMixin):
    """
    SQL Alchemy model for event types
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    title_ar = db.Column(db.String)
    for_actor = db.Column(db.Boolean, default=False)
    for_bulletin = db.Column(db.Boolean, default=False)
    comments = db.Column(db.String)

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the event type."""
        return {
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar or None,
            "for_actor": self.for_actor,
            "for_bulletin": self.for_bulletin,
            "comments": self.comments,
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }

    def to_json(self) -> str:
        """Return a JSON representation of the event type."""
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json: dict[str, Any]) -> "Eventtype":
        """
        Create an event type object from a json dictionary.

        Args:
            - json: the json dictionary to create the event type from.

        Returns:
            - the event type object.
        """
        self.title = json.get("title", self.title)
        self.title_ar = json.get("title_ar", self.title_ar)
        self.for_actor = json.get("for_actor", self.for_actor)
        self.for_bulletin = json.get("for_bulletin", self.for_bulletin)
        self.comments = json.get("comments", self.comments)

        return self

    @staticmethod
    def find_by_title(title: str) -> Optional["Eventtype"]:
        """Return the first event type with the given title."""
        # search
        return Eventtype.query.filter(Eventtype.title.ilike(title.strip())).first()

    # imports data from csv
    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Imports Eventtype data from a CSV file.

        Args:
            - file_storage: the file storage object containing the CSV data.

        Returns:
            - empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        df.comments = df.comments.fillna("")
        db.session.bulk_insert_mappings(Eventtype, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from eventtype").scalar()
        db.session.execute("alter sequence eventtype_id_seq restart with :m", {"m": max_id})
        db.session.commit()
        return ""


class Event(db.Model, BaseMixin):
    """
    SQL Alchemy model for events
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, index=True)
    title_ar = db.Column(db.String, index=True)
    comments = db.Column(db.String)
    comments_ar = db.Column(db.String)

    location_id = db.Column(db.Integer, db.ForeignKey("location.id"))
    location = db.relationship("Location", backref="location_events", foreign_keys=[location_id])
    eventtype_id = db.Column(db.Integer, db.ForeignKey("eventtype.id"))
    eventtype = db.relationship(
        "Eventtype", backref="eventtype_events", foreign_keys=[eventtype_id]
    )
    from_date = db.Column(db.DateTime)
    to_date = db.Column(db.DateTime)
    estimated = db.Column(db.Boolean)

    @staticmethod
    def get_event_filters(
        dates: Optional[list] = None,
        eventtype_id: Optional[t.id] = None,
        event_location_id: Optional[t.id] = None,
    ) -> list:
        """
        Get the filters for querying events based on the given parameters.

        Args:
            - dates: list of dates to filter by.
            - eventtype_id: the event type id to filter by.
            - event_location_id: the event location id to filter by.

        Returns:
            - list of conditions to filter by.
        """
        conditions = []

        if dates:
            start_date = parse(dates[0]).date()
            if len(dates) == 1:
                end_date = start_date
            else:
                end_date = parse(dates[1]).date()

            date_condition = or_(
                and_(
                    func.date(Event.from_date) <= start_date, func.date(Event.to_date) >= end_date
                ),
                func.date(Event.from_date).between(start_date, end_date),
                func.date(Event.to_date).between(start_date, end_date),
            )
            conditions.append(date_condition)

        if event_location_id:
            conditions.append(Event.location_id == event_location_id)
        if eventtype_id:
            conditions.append(Event.eventtype_id == eventtype_id)

        return conditions

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the event."""
        return {
            "id": self.id,
            "title": self.title if self.title else None,
            "title_ar": self.title_ar if self.title_ar else None,
            "comments": self.comments if self.comments else None,
            "comments_ar": self.comments_ar if self.comments_ar else None,
            "location": self.location.to_dict() if self.location else None,
            "eventtype": self.eventtype.to_dict() if self.eventtype else None,
            "from_date": DateHelper.serialize_datetime(self.from_date) if self.from_date else None,
            "to_date": DateHelper.serialize_datetime(self.to_date) if self.to_date else None,
            "estimated": self.estimated if self.estimated else None,
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }

    def to_json(self) -> str:
        """Return a JSON representation of the event."""
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json: dict[str, Any]) -> "Event":
        """
        Create an event object from a json dictionary.

        Args:
            - json: the json dictionary to create the event from.

        Returns:
            - the event object.
        """
        self.title = json["title"] if "title" in json else None
        self.title_ar = json["title_ar"] if "title_ar" in json else None
        self.comments = json["comments"] if "comments" in json else None
        self.comments_ar = json["comments_ar"] if "comments_ar" in json else None

        self.location_id = (
            json["location"]["id"] if "location" in json and json["location"] else None
        )
        self.eventtype_id = (
            json["eventtype"]["id"] if "eventtype" in json and json["eventtype"] else None
        )

        from_date = json.get("from_date", None)
        self.from_date = DateHelper.parse_date(from_date) if from_date else None

        to_date = json.get("to_date", None)
        self.to_date = DateHelper.parse_date(to_date) if to_date else None

        self.estimated = json["estimated"] if "estimated" in json else None

        return self


class Media(db.Model, BaseMixin):
    """
    SQL Alchemy model for media
    """

    # __table_args__ = {"extend_existing": True}

    extend_existing = True

    __table_args__ = (
        db.Index(
            "ix_media_etag_unique_not_deleted",
            "etag",
            unique=True,
            postgresql_where=db.text("deleted = FALSE"),
        ),
    )

    # set media directory here (could be set in the settings)
    media_dir = Path("enferno/media")
    inline_dir = Path("enferno/media/inline")
    id = db.Column(db.Integer, primary_key=True)
    media_file = db.Column(db.String, nullable=False)
    media_file_type = db.Column(db.String, nullable=False)
    category = db.Column(db.Integer)
    etag = db.Column(db.String, index=True)
    duration = db.Column(db.String)

    title = db.Column(db.String)
    title_ar = db.Column(db.String)
    comments = db.Column(db.String)
    comments_ar = db.Column(db.String)
    search = db.Column(
        db.Text,
        db.Computed(
            """
            CAST(id AS TEXT) || ' ' ||
            COALESCE(title, '') || ' ' ||
            COALESCE(media_file, '') || ' ' ||
            COALESCE(media_file_type, '') || ' ' ||
            COALESCE(comments, '')
            """
        ),
    )

    time = db.Column(db.Float(precision=2))

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_medias", foreign_keys=[user_id])

    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"))
    bulletin = db.relationship("Bulletin", backref="medias", foreign_keys=[bulletin_id])

    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"))
    actor = db.relationship("Actor", backref="medias", foreign_keys=[actor_id])

    main = db.Column(db.Boolean, default=False)

    # custom serialization method
    @check_roles
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the media."""
        category_title = None

        # Retrieve category title if self.category exists
        if self.category:
            media_category = MediaCategory.query.get(self.category)
            if media_category:
                category_title = media_category.title
        return {
            "id": self.id,
            "title": self.title if self.title else None,
            "title_ar": self.title_ar if self.title_ar else None,
            "category": category_title if category_title else None,
            "fileType": self.media_file_type if self.media_file_type else None,
            "filename": self.media_file if self.media_file else None,
            "etag": getattr(self, "etag", None),
            "time": getattr(self, "time", None),
            "duration": self.duration,
            "main": self.main,
            "updated_at": DateHelper.serialize_datetime(self.updated_at)
            if self.updated_at
            else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the media."""
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json: dict[str, Any]) -> "Media":
        """
        Create a media object from a json dictionary.

        Args:
            - json: the json dictionary to create the media from.

        Returns:
            - the media object.
        """
        self.title = json["title"] if "title" in json else None
        self.title_ar = json["title_ar"] if "title_ar" in json else None
        self.media_file_type = json["fileType"] if "fileType" in json else None
        self.media_file = json["filename"] if "filename" in json else None
        self.etag = json.get("etag", None)
        self.time = json.get("time", None)
        category = json.get("category", None)
        if category:
            self.category = category.get("id")
        return self

    # generate custom file name for upload purposes
    @staticmethod
    def generate_file_name(filename: str) -> str:
        """
        Generate a secure and timestamped file name.

        Args:
            - filename: the original file name.

        Returns:
            - the generated file name.
        """
        return "{}-{}".format(
            datetime.utcnow().strftime("%Y%m%d-%H%M%S"),
            secure_filename(filename).lower(),
        )

    @staticmethod
    def validate_file_extension(filepath: str, allowed_extensions: list[str]) -> bool:
        """
        Validate file extension against a list of allowed extensions.

        Args:
            - filepath: the path to the file.
            - allowed_extensions: list of allowed file extensions.

        Returns:
            - True if extension is valid, False otherwise.
        """
        extension = pathlib.Path(filepath).suffix.lower().lstrip(".")
        return extension in allowed_extensions


# Structure is copied over from previous system
class Location(db.Model, BaseMixin):
    """
    SQL Alchemy model for locations
    """

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
            "latlng": {"lng": to_shape(self.latlng).x, "lat": to_shape(self.latlng).y}
            if self.latlng
            else None,
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
            "full_string": self.get_full_string(),
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
            self.location_type = LocationType.query.get(self.location_type_id)

            if self.location_type.title == "Administrative Location":
                self.admin_level_id = jsn.get("admin_level").get("id")
                self.admin_level = LocationAdminLevel.query.get(self.admin_level_id)
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
    def get_full_string(self, descending=True):
        """Generates full string of location and parents."""
        pid = self.parent_id
        if not pid or self.admin_level is None:
            return self.title

        string = []
        string.append(self.title)
        counter = self.admin_level.code

        while True:
            if pid:
                parent = Location.query.get(pid)
                if parent:
                    if descending:
                        string.insert(0, parent.title)
                    else:
                        string.append(parent.title)
                    pid = parent.parent_id

            counter -= 1
            if counter == 0:
                break

        return ", ".join(string)

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
        result = db.engine.execute(text(query), id=self.id)
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

    @staticmethod
    def rebuild_id_trees():
        """Rebuild the id tree for all locations."""
        for l in Location.query.all():
            l.id_tree = l.get_id_tree()
            l.save()

        logger.info("Locations ID tree generated successfuly.")

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
        max_id = db.session.execute("select max(id)+1  from location").scalar()
        db.session.execute("alter sequence location_id_seq restart with :m", {"m": max_id})
        db.session.commit()

        return ""


class LocationAdminLevel(db.Model, BaseMixin):
    """
    SQL Alchemy model for location admin levels
    """

    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location admin level."""
        return {"id": self.id, "code": self.code, "title": self.title}

    def from_json(self, jsn: dict[str, Any]) -> "LocationAdminLevel":
        """
        Create a location admin level object from a json dictionary.

        Args:
            - json: the json dictionary to create the location admin level from.
        """
        self.code = jsn.get("code")
        self.title = jsn.get("title")


class LocationType(db.Model, BaseMixin):
    """
    SQL Alchemy model for location types
    """

    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location type."""
        return {"id": self.id, "title": self.title, "description": self.description}

    def from_json(self, jsn: dict[str, Any]) -> "LocationType":
        """
        Create a location type object from a json dictionary.

        Args:
            - json: the json dictionary to create the location type from.
        """
        self.title = jsn.get("title")
        self.description = jsn.get("description")


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


# joint table
bulletin_sources = db.Table(
    "bulletin_sources",
    db.Column("source_id", db.Integer, db.ForeignKey("source.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
)

# joint table
bulletin_locations = db.Table(
    "bulletin_locations",
    db.Column("location_id", db.Integer, db.ForeignKey("location.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
)

# joint table
bulletin_labels = db.Table(
    "bulletin_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
)

# joint table
bulletin_verlabels = db.Table(
    "bulletin_verlabels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
)

# joint table
bulletin_events = db.Table(
    "bulletin_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
)

# joint table
bulletin_roles = db.Table(
    "bulletin_roles",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
)


class Btob(db.Model, BaseMixin):
    """
    Bulletin to bulletin relationship model
    """

    extend_existing = True

    # This constraint will make sure only one relationship exists across bulletins (and prevent self relation)
    __table_args__ = (db.CheckConstraint("bulletin_id < related_bulletin_id"),)

    # Source Bulletin
    # Available Backref: bulletin_from
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Target Bulletin
    # Available Backref: bulletin_to
    related_bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(ARRAY(db.Integer))
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_btobs", foreign_keys=[user_id])

    @property
    def relation_info(self) -> list[dict[str, Any]]:
        """
        Return the relation information.

        Returns:
            - the relation information.
        """
        related_infos = (
            BtobInfo.query.filter(BtobInfo.id.in_(self.related_as)).all() if self.related_as else []
        )
        # Return the to_dict representation of each of them
        return [info.to_dict() for info in related_infos]

    # Check if two bulletins are related , if so return the relation, otherwise false
    @staticmethod
    def are_related(a_id: t.id, b_id: t.id) -> Union["Btob", bool]:
        """
        Check if two bulletins are related.

        Args:
            - a_id: the id of the first bulletin.
            - b_id: the id of the second bulletin.

        Returns:
            - the relation if the bulletins are related, False otherwise.
        """
        if a_id == b_id:
            return False

        # with our id constraint set, just check if there is relation from the lower id to the upper id
        f, t = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        relation = Btob.query.get((f, t))
        if relation:
            return relation
        else:
            return False

    # Give an id, get the other bulletin id (relating in or out)
    def get_other_id(self, id: t.id) -> Optional[t.id]:
        """
        Return the other bulletin id.

        Args:
            - id: the id of the bulletin.

        Returns:
            - the other bulletin id or None.
        """
        if id in (self.bulletin_id, self.related_bulletin_id):
            return self.bulletin_id if id == self.related_bulletin_id else self.related_bulletin_id
        return None

    # Create and return a relation between two bulletins making sure the relation goes from the lower id to the upper id
    @staticmethod
    def relate(a: "Bulletin", b: "Bulletin") -> "Btob":
        """
        Create a relation between two bulletins making sure the relation goes from the lower id to the upper id.

        Args:
            - a: the first bulletin.
            - b: the second bulletin.

        Returns:
            - the relation between the two bulletins.
        """
        f, t = min(a.id, b.id), max(a.id, b.id)
        return Btob(bulletin_id=f, related_bulletin_id=t)

    @staticmethod
    def relate_by_id(a: t.id, b: t.id) -> "Btob":
        """
        Relate two bulletins by their ids.

        Args:
            - a: the id of the first bulletin.
            - b: the id of the second bulletin.

        Returns:
            - the created relation between the two bulletins.
        """
        f, t = min(a, b), max(a, b)
        return Btob(bulletin_id=f, related_bulletin_id=t)

    # Exclude the primary bulletin from output to get only the related/relating bulletin
    @check_relation_roles
    def to_dict(self, exclude: Optional["Bulletin"] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the relation.

        Args:
            - exclude: the bulletin to exclude.

        Returns:
            - the dictionary representation of the relation.
        """
        if not exclude:
            return {
                "bulletin_from": self.bulletin_from.to_compact(),
                "bulletin_to": self.bulletin_to.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }
        else:
            bulletin = self.bulletin_to if exclude == self.bulletin_from else self.bulletin_from

            return {
                "bulletin": bulletin.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation: Optional[dict] = None) -> "Btob":
        """
        Update the relationship data.

        Args:
            - relation: the relation data.

        Returns:
            - the updated relation.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self


class BtobInfo(db.Model, BaseMixin):
    """
    Btob Relation Information Model
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

    def from_json(self, jsn: dict[str, Any]) -> "BtobInfo":
        """
        Create a relation information object from a json dictionary.

        Args:
            - json: the json dictionary to create the relation information from.

        Returns:
            - the relation information object.
        """
        self.title = jsn.get("title", self.title)
        self.reverse_title = jsn.get("reverse_title", self.reverse_title)
        self.title_tr = jsn.get("title_tr", self.title_tr)
        self.reverse_title_tr = jsn.get("reverse_title_tr", self.reverse_title_tr)


# Actor to bulletin uni-direction relation
class Atob(db.Model, BaseMixin):
    """
    Actor to bulletin relationship model
    """

    extend_existing = True

    # Available Backref: bulletin
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Available Backref: actor
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)

    # Relationship extra fields
    # enabling multiple relationship types
    related_as = db.Column(ARRAY(db.Integer))
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_atobs", foreign_keys=[user_id])

    # Exclude the primary bulletin from output to get only the related/relating bulletin
    @property
    def relation_info(self) -> list[dict[str, Any]]:
        # Query the AtobInfo table based on the related_as list
        related_infos = (
            AtobInfo.query.filter(AtobInfo.id.in_(self.related_as)).all() if self.related_as else []
        )
        # Return the to_dict representation of each of them
        return [info.to_dict() for info in related_infos]

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the relation."""
        return {
            "bulletin": self.bulletin.to_compact(),
            "actor": self.actor.to_compact(),
            "related_as": self.related_as or [],
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data
    def from_json(self, relation: Optional[dict[str, Any]] = None) -> "Atob":
        """
        Update the relationship data.

        Args:
            - relation: the relation data.

        Returns:
            - the updated relation.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self


class AtobInfo(db.Model, BaseMixin):
    """
    Atob Relation Information Model
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

    def from_json(self, jsn: dict[str, Any]) -> "AtobInfo":
        """
        Create a relation information object from a json dictionary.

        Args:
            - json: the json dictionary to create the relation information from.

        Returns:
            - the relation information object.
        """
        self.title = jsn.get("title", self.title)
        self.reverse_title = jsn.get("reverse_title", self.reverse_title)
        self.title_tr = jsn.get("title_tr", self.title_tr)
        self.reverse_title_tr = jsn.get("reverse_title_tr", self.reverse_title_tr)


class Atoa(db.Model, BaseMixin):
    """
    Actor to actor relationship model
    """

    extend_existing = True

    # This constraint will make sure only one relationship exists across bulletins (and prevent self relation)
    __table_args__ = (db.CheckConstraint("actor_id < related_actor_id"),)

    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)
    related_actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_atoas", foreign_keys=[user_id])

    @property
    def relation_info(self) -> dict[str, Any]:
        related_info = (
            AtoaInfo.query.filter(AtoaInfo.id == self.related_as).first()
            if self.related_as
            else None
        )
        # Return the to_dict representation of the related_info if it exists, or an empty dictionary if not
        return related_info.to_dict() if related_info else {}

    # helper method to check if two actors are related and returns the relationship
    @staticmethod
    def are_related(a_id: t.id, b_id: t.id) -> Union["Atoa", bool]:
        """
        Check if two actors are related.

        Args:
            - a_id: the id of the first actor.
            - b_id: the id of the second actor.

        Returns:
            - the relation if the actors are related, False otherwise.
        """
        if a_id == b_id:
            return False

        # with our id constraint set, just check if there is relation from the lower id to the upper id
        f, t = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        relation = Atoa.query.get((f, t))
        if relation:
            return relation
        else:
            return False

    # given one actor id, this method will return the other related actor id
    def get_other_id(self, id: t.id) -> Optional[t.id]:
        """
        Return the other actor id.

        Args:
            - id: the id of the actor.

        Returns:
            - the other actor id or None.
        """
        if id in (self.actor_id, self.related_actor_id):
            return self.actor_id if id == self.related_actor_id else self.related_actor_id
        return None

    # Create and return a relation between two actors making sure the relation goes from the lower id to the upper id
    # a = 12 b = 11
    @staticmethod
    def relate(a, b):
        f, t = min(a.id, b.id), max(a.id, b.id)

        return Atoa(actor_id=f, related_actor_id=t)

    # Exclude the primary actor from output to get only the related/relating actor

    # custom serialization method
    @check_relation_roles
    def to_dict(self, exclude: Optional["Actor"] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the relation.

        Args:
            - exclude: the actor to exclude.

        Returns:
            - the dictionary representation of the relation.
        """
        if not exclude:
            return {
                "actor_from": self.actor_from.to_compact(),
                "actor_to": self.actor_to.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }
        else:
            actor = self.actor_to if exclude == self.actor_from else self.actor_from
            return {
                "actor": actor.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation: dict[str, Any] = None) -> "Atoa":
        """
        Return a dictionary representation of the relation.

        Args:
            - relation: the relation data.

        Returns:
            - the updated relation.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self

    def from_etl(self, json):
        pass


class AtoaInfo(db.Model, BaseMixin):
    """
    Atoa Relation Information Model
    """

    extend_existing = True

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    reverse_title = db.Column(db.String, nullable=False)
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

    def from_json(self, jsn: dict[str, Any]) -> "AtoaInfo":
        """
        Create a relation information object from a json dictionary.

        Args:
            - json: the json dictionary to create the relation information from.

        Returns:
            - the relation information object.
        """
        self.title = jsn.get("title", self.title)
        self.reverse_title = jsn.get("reverse_title", self.reverse_title)
        self.title_tr = jsn.get("title_tr", self.title_tr)
        self.reverse_title_tr = jsn.get("reverse_title_tr", self.reverse_title_tr)


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

    # ref field : used for etl tagging etc ..
    ref = db.Column(ARRAY(db.String))

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
        self.ref = json["ref"] if "ref" in json else []

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

        return {
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
            "first_peer_reviewer": self.first_peer_reviewer.to_compact()
            if self.first_peer_reviewer_id
            else None,
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
            "ref": self.ref or None,
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
            "status": self.status,
            "review": self.review if self.review else None,
            "review_action": self.review_action if self.review_action else None,
            "updated_at": DateHelper.serialize_datetime(self.get_modified_date()),
            "roles": [role.to_dict() for role in self.roles] if self.roles else [],
        }

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


# Updated joint table for actor_sources
actor_sources = db.Table(
    "actor_sources",
    db.Column("source_id", db.Integer, db.ForeignKey("source.id"), primary_key=True),
    db.Column(
        "actor_profile_id",
        db.Integer,
        db.ForeignKey("actor_profile.id"),
        primary_key=True,
    ),
)

# joint table for actor_labels
actor_labels = db.Table(
    "actor_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "actor_profile_id",
        db.Integer,
        db.ForeignKey("actor_profile.id"),
        primary_key=True,
    ),
)

# joint table for actor_verlabels
actor_verlabels = db.Table(
    "actor_verlabels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "actor_profile_id",
        db.Integer,
        db.ForeignKey("actor_profile.id"),
        primary_key=True,
    ),
)


# joint table
actor_events = db.Table(
    "actor_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
)

# joint table
actor_roles = db.Table(
    "actor_roles",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
)

actor_countries = db.Table(
    "actor_countries",
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    db.Column("country_id", db.Integer, db.ForeignKey("countries.id"), primary_key=True),
)

actor_ethnographies = db.Table(
    "actor_ethnographies",
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    db.Column("ethnography_id", db.Integer, db.ForeignKey("ethnographies.id"), primary_key=True),
)

actor_dialects = db.Table(
    "actor_dialects",
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    db.Column("dialect_id", db.Integer, db.ForeignKey("dialects.id"), primary_key=True),
)


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

    id_number = db.Column(db.String(255))

    status = db.Column(db.String(255))

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
        db.CheckConstraint("name IS NOT NULL OR name_ar IS NOT NULL", name="check_name"),
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
        return list(set(source for profile in self.actor_profiles for source in profile.sources))

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
        # All text fields

        self.type = json["type"] if "type" in json else None

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
        self.id_number = json["id_number"] if "id_number" in json else None

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
        return {
            "id": self.id,
            "name": self.name,
        }

    def to_csv_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the actor for CSV export."""
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
            "id_number": self.id_number or None,
            # assigned to
            "assigned_to": self.assigned_to.to_compact() if self.assigned_to else None,
            # first peer reviewer
            "first_peer_reviewer": self.first_peer_reviewer.to_compact()
            if self.first_peer_reviewer
            else None,
            "comments": self.comments or None,
            "events": events_json,
            "medias": medias_json,
            "actor_relations": actor_relations_dict,
            "bulletin_relations": bulletin_relations_dict,
            "incident_relations": incident_relations_dict,
            "origin_place": self.origin_place.to_dict() if self.origin_place else None,
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


# Incident to bulletin uni-direction relation
class Itob(db.Model, BaseMixin):
    """
    Incident to bulletin relations model
    """

    extend_existing = True

    # Available Backref: incident
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Available Backref: bulletin
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itobs", foreign_keys=[user_id])

    @property
    def relation_info(self):
        related_info = (
            ItobInfo.query.filter(ItobInfo.id == self.related_as).first()
            if self.related_as
            else None
        )
        # Return the to_dict representation of the related_info if it exists, or an empty dictionary if not
        return related_info.to_dict() if related_info else {}

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the relation."""
        return {
            "bulletin": self.bulletin.to_compact(),
            "incident": self.incident.to_compact(),
            "related_as": self.related_as,
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data
    def from_json(self, relation: Optional[dict[str, Any]] = None) -> "Itob":
        """
        Update the relationship data.

        Args:
            - relation: the relation dictionary.

        Returns:
            - the updated object.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self


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
class Itoa(db.Model, BaseMixin):
    """
    Incident to actor relationship model
    """

    extend_existing = True

    # Available Backref: actor
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)

    # Available Backref: incident
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(ARRAY(db.Integer))
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itoas", foreign_keys=[user_id])

    @property
    def relation_info(self):
        # Query the AtobInfo table based on the related_as list
        related_infos = (
            ItoaInfo.query.filter(ItoaInfo.id.in_(self.related_as)).all() if self.related_as else []
        )
        # Return the to_dict representation of each of them
        return [info.to_dict() for info in related_infos]

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the relation."""
        return {
            "actor": self.actor.to_compact(),
            "incident": self.incident.to_compact(),
            "related_as": self.related_as,
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data, (populates it from json dict)
    def from_json(self, relation: Optional[dict[str, Any]] = None) -> "Itoa":
        """
        Update the relationship data.

        Args:
            - relation: the relation dictionary.

        Returns:
            - the updated object.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self


class ItoaInfo(db.Model, BaseMixin):
    """
    Itoa Relation Information Model
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

    def from_json(self, jsn: dict[str, Any]) -> "ItoaInfo":
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


# incident to incident relationship
class Itoi(db.Model, BaseMixin):
    """
    Incident to incident relation model
    """

    extend_existing = True

    # This constraint will make sure only one relationship exists across bulletins (and prevent self relation)
    __table_args__ = (db.CheckConstraint("incident_id < related_incident_id"),)

    # Source Incident
    # Available Backref: incident_from
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Target Incident
    # Available Backref: Incident_to
    related_incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), primary_key=True)

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itois", foreign_keys=[user_id])

    @property
    def relation_info(self):
        related_info = (
            ItoiInfo.query.filter(ItoiInfo.id == self.related_as).first()
            if self.related_as
            else None
        )
        # Return the to_dict representation of the related_info if it exists, or an empty dictionary if not
        return related_info.to_dict() if related_info else {}

    # Check if two incidents are related , if so return the relation, otherwise false
    @staticmethod
    def are_related(a_id: t.id, b_id: t.id) -> Union["Itoi", bool]:
        """
        Check if two incidents are related.

        Args:
            - a_id: the first incident id.
            - b_id: the second incident id.

        Returns:
            - the relationship if it exists, or False.
        """
        if a_id == b_id:
            return False

        # with our id constraint set, just check if there is relation from the lower id to the upper id
        f, t = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        relation = Itoi.query.get((f, t))
        if relation:
            return relation
        else:
            return False

    # Give an id, get the other bulletin id (relating in or out)
    def get_other_id(self, id: t.id) -> Optional[t.id]:
        """
        Get the other incident id.

        Args:
            - id: the incident id.

        Returns:
            - the other incident id if it exists, or None.
        """
        if id in (self.incident_id, self.related_incident_id):
            return self.incident_id if id == self.related_incident_id else self.related_incident_id
        return None

    # Create and return a relation between two bulletins making sure the relation goes from the lower id to the upper id
    @staticmethod
    def relate(a: "Incident", b: "Incident") -> "Itoi":
        """
        Create a relationship between two incidents.

        Args:
            - a: the first incident.
            - b: the second incident.

        Returns:
            - the relationship.
        """
        f, t = min(a.id, b.id), max(a.id, b.id)
        return Itoi(incident_id=f, related_incident_id=t)

    # custom serialization method
    @check_relation_roles
    def to_dict(self, exclude: Optional["Incident"] = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the relation.

        Args:
            - exclude: the incident to exclude.

        Returns:
            - the dictionary representation of the relation.
        """
        if not exclude:
            return {
                "incident_from": self.incident_from.to_compact(),
                "incident_to": self.incident_to.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }
        else:
            incident = self.incident_to if exclude == self.incident_from else self.incident_from
            return {
                "incident": incident.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation: dict[str, Any] = None) -> "Itoi":
        """
        Update the relationship data.

        Args:
            - relation: the relation dictionary.

        Returns:
            - the updated object.
        """
        if relation:
            self.probability = relation["probability"] if "probability" in relation else None
            self.related_as = relation["related_as"] if "related_as" in relation else None
            self.comment = relation["comment"] if "comment" in relation else None

        return self


class ItoiInfo(db.Model, BaseMixin):
    """
    Itoi Information Model
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

    def from_json(self, jsn: dict[str, Any]) -> "ItoiInfo":
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


class PotentialViolation(db.Model, BaseMixin):
    """
    SQL Alchemy model for potential violations
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    title_ar = db.Column(db.String)

    # to serialize data
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the potential violation."""
        return {"id": self.id, "title": self.title}

    def to_json(self) -> str:
        """Return a JSON representation of the potential violation."""
        return json.dumps(self.to_dict())

    # load from json dit
    def from_json(self, json: dict[str, Any]) -> "PotentialViolation":
        """
        Populate the object from a json dictionary.

        Args:
            - json: the json dictionary.

        Returns:
            - the updated object.
        """
        self.title = json["title"]
        return self

    # import csv data in to db items
    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Import CSV data into the database.

        Args:
            - file_storage: the file storage.

        Returns:
            - an empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        db.session.bulk_insert_mappings(PotentialViolation, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from potential_violation").scalar()
        db.session.execute(
            "alter sequence potential_violation_id_seq restart with :m", {"m": max_id}
        )
        db.session.commit()

        return ""


class ClaimedViolation(db.Model, BaseMixin):
    """
    SQL Alchemy model for claimed violations
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    title_ar = db.Column(db.String)

    # serialize
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the claimed violation."""
        return {"id": self.id, "title": self.title}

    def to_json(self) -> str:
        """Return a JSON representation of the claimed violation."""
        return json.dumps(self.to_dict())

    # populate from json dict
    def from_json(self, json: dict[str, Any]) -> "ClaimedViolation":
        """
        Populate the object from a json dictionary.

        Args:
            - json: the json dictionary.

        Returns:
            - the updated object.
        """
        self.title = json["title"]
        return self

    # import csv data into db items
    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Import CSV data into the database.

        Args:
            - file_storage: the file storage.

        Returns:
            - an empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        db.session.bulk_insert_mappings(ClaimedViolation, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from claimed_violation").scalar()
        db.session.execute("alter sequence claimed_violation_id_seq restart with :m", {"m": max_id})
        db.session.commit()
        logger.info("Claimed Violation imported successfully.")
        return ""


# joint table
incident_locations = db.Table(
    "incident_locations",
    db.Column("location_id", db.Integer, db.ForeignKey("location.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
)

# joint table
incident_labels = db.Table(
    "incident_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
)

# joint table
incident_events = db.Table(
    "incident_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
)

# joint table
incident_potential_violations = db.Table(
    "incident_potential_violations",
    db.Column(
        "potentialviolation_id",
        db.Integer,
        db.ForeignKey("potential_violation.id"),
        primary_key=True,
    ),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
)

# joint table
incident_claimed_violations = db.Table(
    "incident_claimed_violations",
    db.Column(
        "claimedviolation_id", db.Integer, db.ForeignKey("claimed_violation.id"), primary_key=True
    ),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
)

# joint table
incident_roles = db.Table(
    "incident_roles",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
)


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
        # All text fields

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
            "first_peer_reviewer": self.first_peer_reviewer.to_compact()
            if self.first_peer_reviewer
            else None,
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


class BulletinHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for bulletin revisions
    """

    id = db.Column(db.Integer, primary_key=True)
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), index=True)
    bulletin = db.relationship(
        "Bulletin",
        backref=db.backref("history", order_by="BulletinHistory.updated_at"),
        foreign_keys=[bulletin_id],
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="bulletin_revisions", foreign_keys=[user_id])

    @property
    def restricted_data(self):
        return {
            "comments": self.data.get("comments"),
            "status": self.data.get("status"),
        }

    # serialize
    @check_history_access
    def to_dict(self, full=False) -> dict[str, Any]:
        """
        Return a dictionary representation of the bulletin revision.
        """
        return {
            "id": self.id,
            "data": self.data if full else self.restricted_data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the bulletin revision."""
        return json.dumps(self.to_dict(), sort_keys=True)

    def __repr__(self):
        return "<BulletinHistory {} -- Target {}>".format(self.id, self.bulletin_id)


# --------------------------------- Actors History + Indexers -------------------------------------


class ActorHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for actor revisions
    """

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), index=True)
    actor = db.relationship(
        "Actor",
        backref=db.backref("history", order_by="ActorHistory.updated_at"),
        foreign_keys=[actor_id],
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="actor_revisions", foreign_keys=[user_id])

    @property
    def restricted_data(self):
        return {
            "comments": self.data.get("comments"),
            "status": self.data.get("status"),
        }

    # serialize
    @check_history_access
    def to_dict(self, full=False) -> dict[str, Any]:
        """Return a dictionary representation of the actor revision."""
        return {
            "id": self.id,
            "data": self.data if full else self.restricted_data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the actor revision."""
        return json.dumps(self.to_dict(), sort_keys=True)


# --------------------------------- Incident History + Indexers -------------------------------------


class IncidentHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for incident revisions
    """

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), index=True)
    incident = db.relationship(
        "Incident",
        backref=db.backref("history", order_by="IncidentHistory.updated_at"),
        foreign_keys=[incident_id],
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="incident_revisions", foreign_keys=[user_id])

    @property
    def restricted_data(self):
        return {
            "comments": self.data.get("comments"),
            "status": self.data.get("status"),
        }

    # serialize
    @check_history_access
    def to_dict(self, full=False) -> dict[str, Any]:
        """Return a dictionary representation of the incident revision."""
        return {
            "id": self.id,
            "data": self.data if full else self.restricted_data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the incident revision."""
        return json.dumps(self.to_dict(), sort_keys=True)


class LocationHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for location revisions
    """

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), index=True)
    location = db.relationship(
        "Location",
        backref=db.backref("history", order_by="LocationHistory.updated_at"),
        foreign_keys=[location_id],
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="location_revisions", foreign_keys=[user_id])

    # serialize
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location revision."""
        return {
            "id": self.id,
            "data": self.data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the location revision."""
        return json.dumps(self.to_dict(), sort_keys=True)

    def __repr__(self):
        return "<LocationHistory {} -- Target {}>".format(self.id, self.location_id)


class Activity(db.Model, BaseMixin):
    """
    SQL Alchemy model for activity
    """

    STATUS_SUCCESS = "SUCCESS"
    STATUS_DENIED = "DENIED"

    ACTION_VIEW = "VIEW"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_CREATE = "CREATE"
    ACTION_REVIEW = "REVIEW"
    ACTION_UPLOAD = "UPLOAD"
    ACTION_BULK_UPDATE = "BULK"
    ACTION_REQUEST_EXPORT = "REQUEST"
    ACTION_APPROVE_EXPORT = "APPROVE"
    ACTION_REJECT_EXPORT = "REJECT"
    ACTION_DOWNLOAD = "DOWNLOAD"
    ACTION_SEARCH = "SEARCH"
    ACTION_SELF_ASSIGN = "SELF-ASSIGN"
    ACTION_LOGIN = "LOGIN"
    ACTION_LOGOUT = "LOGOUT"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    action = db.Column(db.String(100))
    status = db.Column(db.String(100))
    model = db.Column(db.String(100))
    subject = db.Column(JSON)
    details = db.Column(db.Text)

    @staticmethod
    def get_action_values() -> list[str]:
        """Return a list of action values."""
        return [getattr(Activity, attr) for attr in dir(Activity) if attr.startswith("ACTION_")]

    # serialize data
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the activity."""
        # Ensure self.subject is a dictionary.
        if isinstance(self.subject, dict) and self.subject.get("class") == "user":
            user_id = self.subject.get("id")
            if user_id:
                user = User.query.get(user_id)
                if user:
                    # Directly add the username to the subject dictionary.
                    self.subject["username"] = user.username

        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "status": self.status,
            "subject": self.subject,  # Now includes the username if applicable.
            "model": self.model,
            "details": self.details,
            "created_at": DateHelper.serialize_datetime(self.created_at),
        }

    # helper static method to create different type of activities (tags)
    @staticmethod
    def create(
        user: t.id,
        action: str,
        status: str,
        subject: str,
        model: str,
        details: Optional[str] = None,
    ) -> None:
        """
        Create an activity.

        Args:
            - user: the user id.
            - action: the action.
            - status: the status.
            - subject: the subject.
            - model: the model.
            - details: the details.
        """
        # this will check if the action is
        # enabled in system settings
        # if disabled the activity will not be logged
        # denied actions will be always logged
        if not status == Activity.STATUS_DENIED and not action in cfg.activities:
            return

        try:
            activity = Activity()
            activity.user_id = user.id
            activity.action = action
            activity.status = status
            activity.subject = subject
            activity.model = model
            activity.details = details
            activity.save()

        except Exception:
            logger.error("Error creating activity", exc_info=True)


class Settings(db.Model, BaseMixin):
    """User Specific Settings. (SQL Alchemy model)"""

    id = db.Column(db.Integer, primary_key=True)
    darkmode = db.Column(db.Boolean, default=False)


class Query(db.Model, BaseMixin):
    """
    SQL Alchemy model for saved searches
    """

    TYPES = [Bulletin.__tablename__, Actor.__tablename__, Incident.__tablename__]

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="unique_user_queryname"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="queries", foreign_keys=[user_id])
    data = db.Column(JSON)
    query_type = db.Column(db.String, nullable=False, default=Bulletin.__tablename__)

    # serialize data
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the query."""
        return {"id": self.id, "name": self.name, "data": self.data, "query_type": self.query_type}

    def to_json(self) -> str:
        """Return a JSON representation of the query."""
        return json.dumps(self.to_dict())


class Country(db.Model, ComponentDataMixin):
    __tablename__ = "countries"


class Ethnography(db.Model, ComponentDataMixin):
    __tablename__ = "ethnographies"


class Dialect(db.Model, ComponentDataMixin):
    __tablename__ = "dialects"


class MediaCategory(db.Model, ComponentDataMixin):
    __tablename__ = "media_categories"


class GeoLocationType(db.Model, ComponentDataMixin):
    __tablename__ = "geo_location_types"


class WorkflowStatus(db.Model, ComponentDataMixin):
    __tablename__ = "workflow_statuses"


class AppConfig(db.Model, BaseMixin):
    """Global Application Settings. (SQL Alchemy model)"""

    id = db.Column(db.Integer, primary_key=True)
    config = db.Column(JSON, nullable=False)

    # add user reference
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_configs", foreign_keys=[user_id])

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the app config."""
        return {
            "id": self.id,
            "config": self.config,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_dict() if self.user else {},
        }
