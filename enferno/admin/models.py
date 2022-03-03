# import datetime
import json
import os, re
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
from flask_login import current_user
from sqlalchemy import JSON, ARRAY
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.utils import secure_filename
from flask_babelex import gettext

from enferno.extensions import db
from enferno.settings import ProdConfig, DevConfig
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape

# Load configuraitons based on environment settings
if os.getenv("FLASK_DEBUG") == '0':
    cfg = ProdConfig
else:
    cfg = DevConfig


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

    # populate object from json dict
    def from_json(self, json):
        self.title = json["title"]
        if "title_ar" in json:
            self.title_ar = json["title_ar"]
        if "comments" in json:
            self.comments = json["comments"]
        if "comments_ar" in json:
            self.comments = json["comments_ar"]
        parent = json.get('parent')
        if parent:
            self.parent_id = parent.get("id")
        else:
            self.parent_id = None
        return self

    # custom serialization method
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "etl_id": self.etl_id,
            "parent": {"id": self.parent.id, "title": self.parent.title}
            if self.parent
            else None,
            "comments": self.comments,
        }

    def __repr__(self):
        return '<Source {} {}>'.format(self.id, self.title)

    def to_json(self):
        return json.dumps(self.to_dict())

    @staticmethod
    def search(kw):
        """
        Enhanced method to search all hierarchy from the db side, using raw sql query instead of the orm.
        :return: matching records
        """
        query = """
            with  recursive lcte (id, parent_id, title) as (
            select id, parent_id, title from source where title ilike '%%{}%%' union all 
            select x.id, x.parent_id, x.title from lcte c, source x where x.parent_id = c.id)
            select * from lcte;
            """.format(kw)
        result = db.engine.execute(query)

        return [{'id': x[0], 'title': x[2]} for x in result]

    @staticmethod
    def find_by_ids(ids: list):
        """
        finds all items and subitems of a given list of ids, using raw sql query instead of the orm.
        :return: matching records
        """
        if not ids:
            return []
        if len(ids) == 1:
            qstr = '= {} '.format(ids[0])
        else:
            qstr = 'in {} '.format(str(tuple(ids)))
        query = """
               with  recursive lcte (id, parent_id, title) as (
               select id, parent_id, title from source where id {} union all 
               select x.id, x.parent_id, x.title from lcte c, source x where x.parent_id = c.id)
               select * from lcte;
               """.format(qstr)
        result = db.engine.execute(query)

        return [{'id': x[0], 'title': x[2]} for x in result]

    @staticmethod
    def get_children(sources, depth=3):
        all = []
        targets = sources
        while depth != 0:
            children = Source.get_direct_children(targets)
            all += children
            targets = children
            depth -= 1
        return all

    @staticmethod
    def get_direct_children(sources):
        children = []
        for source in sources:
            children += source.sub_source
        return children

    @staticmethod
    def find_by_title(title):
        ar = Source.query.filter(Source.title_ar.ilike(title)).first()
        if ar:
            return ar
        else:
            return Source.query.filter(Source.title.ilike(title)).first()

    # import csv data into db
    @staticmethod
    def import_csv(file_storage):
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.comments = df.comments.fillna("")
        # print (df.to_dict(orient='records')[:10])
        db.session.bulk_insert_mappings(Source, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from source").scalar()
        db.session.execute(
            "alter sequence source_id_seq restart with {}".format(max_id)
        )
        db.session.commit()
        print("Source ID counter updated.")

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

    parent_label_id = db.Column(
        db.Integer, db.ForeignKey("label.id"), index=True, nullable=True
    )
    parent = db.relationship("Label", remote_side=id, backref="sub_label")

    # custom serialization method
    def to_dict(self, mode='1'):
        if mode == '2':
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
            "parent": {"id": self.parent.id, "title": self.parent.title}
            if self.parent else None
        }

    # custom compact serialization
    def to_mode2(self):
        return {
            "id": self.id,
            "title": self.title,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def __repr__(self):
        return '<Label {} {}>'.format(self.id, self.title)

    @staticmethod
    def search(kw):
        """
        Enhanced method to search all hierarchy from the db side, using raw sql query instead of the orm.
        :return: matching records
        """
        query = """
               with  recursive lcte (id, parent_id, title) as (
               select id, parent_label_id, title from label where title ilike '%%{}%%' union all 
               select x.id, x.parent_label_id, x.title from lcte c, label x where x.parent_label_id = c.id)
               select * from lcte;
               """.format(kw)
        result = db.engine.execute(query)

        return [{'id': x[0], 'title': x[2]} for x in result]

    @staticmethod
    def find_by_ids(ids: list):
        """
        finds all items and subitems of a given list of ids, using raw sql query instead of the orm.
        :return: matching records
        """
        if not ids:
            return []
        if len(ids) == 1:
            qstr = '= {} '.format(ids[0])
        else:
            qstr = 'in {} '.format(str(tuple(ids)))

        query = """
                  with  recursive lcte (id, parent_label_id, title) as (
                  select id, parent_label_id, title from label where id {} union all 
                  select x.id, x.parent_label_id, x.title from lcte c, label x where x.parent_label_id = c.id)
                  select * from lcte;
                  """.format(qstr)
        result = db.engine.execute(query)

        return [{'id': x[0], 'title': x[2]} for x in result]

    @staticmethod
    def get_children(labels, depth=3):
        all = []
        targets = labels
        while depth != 0:
            children = Label.get_direct_children(targets)
            all += children
            targets = children
            depth -= 1
        return all

    @staticmethod
    def get_direct_children(labels):
        children = []
        for label in labels:
            children += label.sub_label
        return children

    @staticmethod
    def find_by_title(title):
        ar = Label.query.filter(Label.title_ar.ilike(title)).first()
        if ar:
            return ar
        else:
            return Label.query.filter(Label.title.ilike(title)).first()

    # populate object from json data
    def from_json(self, json):
        self.title = json["title"]
        self.title_ar = json["title_ar"] if "title_ar" in json else ""
        self.comments = json["comments"] if "comments" in json else ""
        self.comments_ar = json["comments_ar"] if "comments_ar" in json else ""
        self.verified = json.get("verified", False)
        self.for_bulletin = json.get("for_bulletin", False)
        self.for_actor = json.get("for_actor", False)
        self.for_incident = json.get("for_incident", False)
        self.for_offline = json.get("for_offline", False)
        parent = json.get('parent')
        # reject associating label with itself
        if parent and parent.get('id') and parent.get('id') != self.id:
            self.parent_label_id = parent.get('id')
        else:
            self.parent_label_id = None
        return self

    # import csv data into db
    @staticmethod
    def import_csv(file_storage):
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.order.astype(int)

        # first ignore foreign key constraints
        dfi = df.copy()
        del dfi['parent_label_id']

        # first insert
        db.session.bulk_insert_mappings(Label, dfi.to_dict(orient="records"))

        # then drop labels with no foreign keys and update
        df = df[df['parent_label_id'].notna()]
        db.session.bulk_update_mappings(Label, df.to_dict(orient="records"))
        db.session.commit()
        
        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from label").scalar()
        db.session.execute("alter sequence label_id_seq restart with {}".format(max_id))
        db.session.commit()
        print("Label ID counter updated.")
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
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar or None,
            "for_actor": self.for_actor,
            "for_bulletin": self.for_bulletin,
            "comments": self.comments

        }

    def to_json(self):
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json):
        self.title = json.get("title", self.title)
        self.title_ar = json.get("title_ar", self.title_ar)
        self.for_actor = json.get("for_actor", self.for_actor)
        self.for_bulletin = json.get("for_bulletin", self.for_bulletin)
        self.comments = json.get("comments", self.comments)

        return self

    @staticmethod
    def find_by_title(title):
        # search
        return Eventtype.query.filter(Eventtype.title.ilike(title.strip())).first()

    # imports data from csv
    @staticmethod
    def import_csv(file_storage):
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        df.comments = df.comments.fillna("")
        db.session.bulk_insert_mappings(Eventtype, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from eventtype").scalar()
        db.session.execute(
            "alter sequence eventtype_id_seq restart with {}".format(max_id)
        )
        db.session.commit()
        print("Eventtype ID counter updated.")
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
    location = db.relationship(
        "Location", backref="location_events", foreign_keys=[location_id]
    )
    eventtype_id = db.Column(db.Integer, db.ForeignKey("eventtype.id"))
    eventtype = db.relationship(
        "Eventtype", backref="eventtype_events", foreign_keys=[eventtype_id]
    )
    from_date = db.Column(db.DateTime)
    to_date = db.Column(db.DateTime)
    estimated = db.Column(db.Boolean)

    # custom serialization method
    def to_dict(self):
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
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json):

        self.title = json["title"] if "title" in json else None
        self.title_ar = json["title_ar"] if "title_ar" in json else None
        self.comments = json["comments"] if "comments" in json else None
        self.comments_ar = json["comments_ar"] if "comments_ar" in json else None

        if "location" in json:
            if json["location"]:
                self.location_id = json["location"]["id"]
        if "eventtype" in json:
            if json["eventtype"]:
                self.eventtype_id = json["eventtype"]["id"]

        from_date = json.get('from_date', None)
        if from_date:
            self.from_date = DateHelper.parse_date(from_date)

        to_date = json.get('to_date', None)
        if to_date:
            self.to_date = DateHelper.parse_date(to_date)

        if "estimated" in json:
            self.estimated = json["estimated"]

        return self


class Media(db.Model, BaseMixin):
    """
    SQL Alchemy model for media
    """
    __table_args__ = {"extend_existing": True}

    # set media directory here (could be set in the settings)
    media_dir = Path("enferno/media")

    id = db.Column(db.Integer, primary_key=True)
    media_file = db.Column(db.String, nullable=False)
    media_file_type = db.Column(db.String, nullable=False)
    category = db.Column(db.String)
    etag = db.Column(db.String, unique=True)
    duration = db.Column(db.String)

    title = db.Column(db.String)
    title_ar = db.Column(db.String)
    comments = db.Column(db.String)
    comments_ar = db.Column(db.String)

    time = db.Column(db.Float(precision=2))

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_medias", foreign_keys=[user_id])

    # custom serialization method
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title if self.title else None,
            "title_ar": self.title_ar if self.title_ar else None,
            "fileType": self.media_file_type if self.media_file_type else None,
            "filename": self.media_file if self.media_file else None,
            "etag": getattr(self, 'etag', None),
            "time": getattr(self, 'time', None),
            "duration": self.duration
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json):
        self.title = json["title"] if "title" in json else None
        self.title_ar = json["title_ar"] if "title_ar" in json else None
        self.media_file_type = json["fileType"] if "fileType" in json else None
        self.media_file = json["filename"] if "filename" in json else None
        self.etag = json.get('etag', None)
        self.time = json.get('time', None)
        return self

    # generate custom file name for upload purposes
    @staticmethod
    def generate_file_name(filename):
        return "{}-{}".format(
            datetime.utcnow().strftime("%Y%m%d-%H%M%S"),
            secure_filename(filename).lower(),
        )


# Structure is copied over from previous system
class Location(db.Model, BaseMixin):
    """
    SQL Alchemy model for locations
    """
    __table_args__ = {"extend_existing": True}

    LOC_TYPE = {
        "G": "Governates",
        "D": "Districts",
        "S": "Subdistricts",
        "C": "Cities",
        "N": "Neighborhoods",
    }

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    title_ar = db.Column(db.String)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    loc_type = db.Column(db.String)
    parent_text = db.Column(db.String)
    description = db.Column(db.Text)
    location_created = db.Column(
        db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )
    location_modified = db.Column(
        db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )
    pcode = db.Column(db.String)

    parent_location_id = db.Column(
        db.Integer, db.ForeignKey("location.id"), index=True, nullable=True
    )
    parent = db.relationship("Location", remote_side=id, backref="sub_location")

    parent_g_en = db.Column(db.String)
    parent_d_en = db.Column(db.String)
    parent_s_en = db.Column(db.String)
    parent_c_en = db.Column(db.String)

    parent_g_ar = db.Column(db.String)
    parent_d_ar = db.Column(db.String)
    parent_s_ar = db.Column(db.String)
    parent_c_ar = db.Column(db.String)

    parent_g_id = db.Column(db.Integer)
    parent_d_id = db.Column(db.Integer)
    parent_s_id = db.Column(db.Integer)
    parent_c_id = db.Column(db.Integer)

    country_cd = db.Column(db.String)

    full_location = db.Column(db.String)

    @staticmethod
    def find_by_ids(ids: list):
        """
        finds all items and subitems of a given list of ids, using raw sql query instead of the orm.
        :return: matching records
        """
        if not ids:
            return []
        if len(ids) == 1:
            qstr = '= {} '.format(ids[0])
        else:
            qstr = 'in {} '.format(str(tuple(ids)))
        query = """
                  with  recursive lcte (id, parent_g_id,parent_d_id, parent_s_id, parent_c_id, title) as (
                  select id, parent_g_id,parent_d_id, parent_s_id, parent_c_id, title from location where id {} union all 
                  select x.id, x.parent_g_id, x.parent_d_id, x.parent_s_id, x.parent_c_id, x.title from lcte c, location x 
                  where x.parent_g_id = c.id or x.parent_d_id = c.id or x.parent_s_id = c.id or x.parent_c_id = c.id)
                  select * from lcte;
                  """.format(qstr)
        result = db.engine.execute(query)

        return [{'id': x[0], 'title': x[5]} for x in result]

    def find_children(self, include_self=True):
        """
        Helper method to find all child location
        :return: list of ids for all child locations
        """
        if self.loc_type == 'G':
            childs = self.query.filter_by(parent_g_id=self.id)

        elif self.loc_type == 'D':
            childs = self.query.filter_by(parent_d_id=self.id)

        elif self.loc_type == 'S':
            childs = self.query.filter_by(parent_s_id=self.id)

        elif self.loc_type == 'C':
            childs = self.query.filter_by(parent_c_id=self.id)

        else:
            if include_self:
                return [self.id]
            else:
                return []
        if include_self:

            return [c.id for c in childs] + [self.id]
        else:
            return [c.id for c in childs]

    @staticmethod
    def find_by_title(title):
        ar = Location.query.filter(Location.title_ar.ilike(title)).first()
        if ar:
            return ar
        else:
            return Location.query.filter(Location.title.ilike(title)).first()

    # custom serialization method
    def to_dict(self):
        parent_g = None
        if self.parent_g_id:
            parent_g_ = self.query.get(self.parent_g_id)
            parent_g = {
                'id': self.parent_g_id,
                'full_string': parent_g_.full_location
            }

        parent_s = None
        if self.parent_s_id:
            parent_s_ = self.query.get(self.parent_s_id)
            parent_s = {
                'id': self.parent_s_id,
                'full_string': parent_s_.full_location
            }

        parent_d = None
        if self.parent_d_id:
            parent_d_ = self.query.get(self.parent_d_id)
            parent_d = {
                'id': self.parent_d_id,
                'full_string': parent_d_.full_location
            }

        parent_c = None
        if self.parent_c_id:
            parent_c_ = self.query.get(self.parent_c_id)
            parent_c = {
                'id': self.parent_c_id,
                'full_string': parent_c_.full_location
            }

        return {
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar,
            "loc_type": self.loc_type,
            "loc_type_name": self.LOC_TYPE[self.loc_type]
            if self.loc_type in self.LOC_TYPE.keys()
            else "",
            "lat": self.latitude,
            "lng": self.longitude,
            "parent_g": parent_g,
            "parent_d": parent_d,
            "parent_s": parent_s,
            "parent_c": parent_c,
            "parent": {"id": self.parent.id, "title": self.parent.title, }
            if self.parent
            else None,
            "full_string": '{} | {}'.format(self.full_location or '', self.title_ar or ''),
        }

    # custom compact serialization method
    def min_json(self):
        return {
            'id': self.id,
            'loc_type': self.loc_type,
            'full_string': '{} | {}'.format(self.full_location, self.title_ar)
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    # populate model from json dict
    def from_json(self, jsn):
        self.title = jsn.get('title')
        self.title_ar = jsn.get('title_ar')
        self.loc_type = jsn.get('loc_type')
        self.longitude = jsn.get('lng')
        self.latitude = jsn.get('lat')
        if jsn.get('parent_g') and jsn.get('parent_g').get('id'):
            self.parent_g_id = jsn.get('parent_g').get('id')
        else:
            self.parent_g_id = None
        if jsn.get('parent_s') and jsn.get('parent_s').get('id'):
            self.parent_s_id = jsn.get('parent_s').get('id')
        else:
            self.parent_s_id = None
        if jsn.get('parent_d') and jsn.get('parent_d').get('id'):
            self.parent_d_id = jsn.get('parent_d').get('id')
        else:
            self.parent_d_id = None
        if jsn.get('parent_c') and jsn.get('parent_c').get('id'):
            self.parent_c_id = jsn.get('parent_c').get('id')
        else:
            self.parent_c_id = None
        parent = jsn.get('parent')
        if parent and parent.get('id'):
            self.parent_location_id = parent.get('id')
        else:
            self.parent_location_id = None

        return self

    # helper method
    def get_sub_locations(self):
        if not self.sub_location:
            return [self]
        else:
            locations = [self]
            for l in self.sub_location:
                locations += [l] + l.get_sub_locations()
            return locations

    # helper method to get full location hierarchy
    def get_full_string(self):
        name_str = str(self.title)
        if self.loc_type == "D" and self.parent_g_id:
            name_str = '{}, {}'.format(self.query.get(self.parent_g_id).title, self.title)
        if self.loc_type == "S" and self.parent_g_id and self.parent_d_id:
            name_str = '{}, {}, {}'.format(self.query.get(self.parent_g_id).title,
                                           self.query.get(self.parent_d_id).title, self.title)
        if self.loc_type == "C" and self.parent_g_id and self.parent_d_id and self.parent_s_id:
            name_str = '{}, {}, {}, {}'.format(self.query.get(self.parent_g_id).title,
                                               self.query.get(self.parent_d_id).title,
                                               self.query.get(self.parent_s_id).title, self.title)
        if self.loc_type == "N" and self.parent_g_id and self.parent_d_id and self.parent_s_id and self.parent_c_id:
            name_str = '{}, {}, {}, {}, {}'.format(self.query.get(self.parent_g_id).title,
                                                   self.query.get(self.parent_d_id).title,
                                                   self.query.get(self.parent_s_id).title,
                                                   self.query.get(self.parent_c_id).title, self.title)
        return name_str

    # imports csv data into db
    @staticmethod
    def import_csv(file_storage):
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)

        # Replace NaN with proper defaults

        df.loc_type = df.loc_type.fillna("")
        df.title = df.title.fillna("")
        df.title_ar = df.title_ar.fillna("")

        df.parent_location_id = df.parent_location_id.fillna(0)
        df.parent_g_id = df.parent_g_id.fillna(0)
        df.parent_d_id = df.parent_d_id.fillna(0)
        df.parent_s_id = df.parent_s_id.fillna(0)
        df.parent_c_id = df.parent_c_id.fillna(0)

        df.parent_d_id = df.parent_d_id.fillna(0)

        db.session.bulk_insert_mappings(
            Location, df.to_dict(orient="records"), render_nulls=True
        )
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from location").scalar()
        db.session.execute(
            "alter sequence location_id_seq restart with {}".format(max_id)
        )
        db.session.commit()
        print("Location ID counter updated.")

        # generate locations full strings
        for location in Location.query.all():
            location.full_location = location.get_full_string()
            print('generating full location string')

        db.session.commit()

        return ""


class GeoLocation(db.Model, BaseMixin):
    """
        SQL Alchemy model for Geo markers (improved location class)
    """
    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    type = db.Column(db.String)
    comment = db.Column(db.Text)
    latlng = db.Column(Geometry('POINT'))
    bulletin_id = db.Column(db.Integer, db.ForeignKey('bulletin.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'lat': to_shape(self.latlng).x,
            'lng': to_shape(self.latlng).y,
            'comment': self.comment
        }


# joint table
bulletin_sources = db.Table(
    "bulletin_sources",
    db.Column("source_id", db.Integer, db.ForeignKey("source.id"), primary_key=True),
    db.Column(
        "bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True
    ),
)

# joint table
bulletin_locations = db.Table(
    "bulletin_locations",
    db.Column(
        "location_id", db.Integer, db.ForeignKey("location.id"), primary_key=True
    ),
    db.Column(
        "bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True
    ),
)

# joint table
bulletin_labels = db.Table(
    "bulletin_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True
    ),
)

# joint table
bulletin_verlabels = db.Table(
    "bulletin_verlabels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True
    ),
)

# joint table
bulletin_events = db.Table(
    "bulletin_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column(
        "bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True
    ),
)

# joint table
bulletin_medias = db.Table(
    "bulletin_medias",
    db.Column("media_id", db.Integer, db.ForeignKey("media.id"), primary_key=True),
    db.Column(
        "bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True
    ),
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
    related_bulletin_id = db.Column(
        db.Integer, db.ForeignKey("bulletin.id"), primary_key=True
    )

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_btobs", foreign_keys=[user_id])

    # Check if two bulletins are related , if so return the relation, otherwise false
    @staticmethod
    def are_related(a_id, b_id):

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
    def get_other_id(self, id):
        if id in (self.bulletin_id, self.related_bulletin_id):
            return (
                self.bulletin_id
                if id == self.related_bulletin_id
                else self.related_bulletin_id
            )
        return None

    # Create and return a relation between two bulletins making sure the relation goes from the lower id to the upper id
    @staticmethod
    def relate(a, b):
        f, t = min(a.id, b.id), max(a.id, b.id)
        return Btob(bulletin_id=f, related_bulletin_id=t)

    # Exclude the primary bulletin from output to get only the related/relating bulletin

    def to_dict(self, exclude=None):
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
            bulletin = (
                self.bulletin_to
                if exclude == self.bulletin_from
                else self.bulletin_from
            )
            return {
                "bulletin": bulletin.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation=None):
        if relation:
            self.probability = (
                relation["probability"] if "probability" in relation else None
            )
            self.related_as = (
                relation["related_as"] if "related_as" in relation else None
            )
            self.comment = relation["comment"] if "comment" in relation else None
            print("Relation has been updated.")
        else:
            print("Relation was not updated.")
        return self


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

    # custom serialization method
    def to_dict(self):

        return {
            "bulletin": self.bulletin.to_compact(),
            "actor": self.actor.to_compact(),
            "related_as": self.related_as if self.related_as else [],
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data
    def from_json(self, relation=None):
        if relation:
            self.probability = (
                relation["probability"] if "probability" in relation else None
            )
            self.related_as = (
                relation["related_as"] if "related_as" in relation else None
            )
            self.comment = relation["comment"] if "comment" in relation else None
            print("Relation has been updated.")
        else:
            print("Relation was not updated.")
        return self


class Atoa(db.Model, BaseMixin):
    """
    Actor to actor relationship model
    """
    extend_existing = True

    # This constraint will make sure only one relationship exists across bulletins (and prevent self relation)
    __table_args__ = (db.CheckConstraint("actor_id < related_actor_id"),)

    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), primary_key=True)
    related_actor_id = db.Column(
        db.Integer, db.ForeignKey("actor.id"), primary_key=True
    )

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_atoas", foreign_keys=[user_id])

    # helper method to check if two actors are related and returns the relationship
    @staticmethod
    def are_related(a_id, b_id):

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
    def get_other_id(self, id):
        if id in (self.actor_id, self.related_actor_id):
            return (
                self.actor_id if id == self.related_actor_id else self.related_actor_id
            )
        return None

    # Create and return a relation between two actors making sure the relation goes from the lower id to the upper id
    # a = 12 b = 11
    @staticmethod
    def relate(a, b):
        f, t = min(a.id, b.id), max(a.id, b.id)

        return Atoa(actor_id=f, related_actor_id=t)

    # Exclude the primary actor from output to get only the related/relating actor

    # custom serialization method
    def to_dict(self, exclude=None):
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
    def from_json(self, relation=None):
        if relation:
            print(self.actor_id, self.related_actor_id, self.related_as)
            self.probability = (
                relation["probability"] if "probability" in relation else None
            )
            self.related_as = (
                relation["related_as"] if "related_as" in relation else None
            )
            self.comment = relation["comment"] if "comment" in relation else None
            print("Relation has been updated.")
        else:
            print("Relation was not updated.")
        return self

    def from_etl(self, json):
        pass


class Bulletin(db.Model, BaseMixin):
    """
    SQL Alchemy model for bulletins
    """
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
        "GeoLocation", backref="bulletin",
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
    )

    medias = db.relationship(
        "Media",
        secondary=bulletin_medias,
        backref=db.backref("bulletins", lazy="dynamic"),
    )

    # Bulletins that this bulletin relate to ->
    bulletins_to = db.relationship(
        "Btob", backref="bulletin_from", foreign_keys="Btob.bulletin_id"
    )

    # Bulletins that relate to this <-
    bulletins_from = db.relationship(
        "Btob", backref="bulletin_to", foreign_keys="Btob.related_bulletin_id"
    )

    # Related Actors
    related_actors = db.relationship(
        "Atob", backref="bulletin", foreign_keys="Atob.bulletin_id"
    )

    # Related Incidents
    related_incidents = db.relationship(
        "Itob", backref="bulletin", foreign_keys="Itob.bulletin_id"
    )

    publish_date = db.Column(
        db.DateTime, index=True
    )
    documentation_date = db.Column(
        db.DateTime, index=True
    )

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

    tsv = db.Column(TSVECTOR)

    search = db.Column(db.Text, db.Computed(
        '''
        (((((((((((((((((id)::text || ' '::text) || (COALESCE(title, ''::character varying))::text) || ' '::text) ||
                        (COALESCE(title_ar, ''::character varying))::text) || ' '::text) ||
                      COALESCE(description, ''::text)) || ' '::text) ||
                    (COALESCE(originid, ''::character varying))::text) || ' '::text) ||
                  (COALESCE(sjac_title, ''::character varying))::text) || ' '::text) ||
                (COALESCE(sjac_title_ar, ''::character varying))::text) || ' '::text) ||
                (COALESCE(source_link, ''::character varying))::text) || ' '::text) 
                ||  ' '::text) || COALESCE(comments, ''::text)
        '''
    ))

    __table_args__ = (
        db.Index('ix_bulletin_search', 'search', postgresql_using="gin", postgresql_ops={'search': 'gin_trgm_ops'}),
    )

    # custom method to create new revision in history table
    def create_revision(self, user_id=None, created=None):
        if not user_id:
            user_id = getattr(current_user, 'id', 1)
        b = BulletinHistory(
            bulletin_id=self.id, data=self.to_dict(), user_id=user_id
        )
        if created:
            b.created_at = created
            b.updated_at = created
        b.save()

        print("created bulletin revision")

    # helper property returns all bulletin relations
    @property
    def bulletin_relations(self):
        return self.bulletins_to + self.bulletins_from

    # helper property returns all actor relations
    @property
    def actor_relations(self):
        return self.related_actors

    # helper property returns all incident relations
    @property
    def incident_relations(self):
        return self.related_incidents

    # populate object from json dict
    def from_json(self, json):
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
        self.source_link_type = json.get('source_link_type', False)
        self.ref = json["ref"] if "ref" in json else []

        # Locations
        if "locations" in json:
            ids = [location["id"] for location in json["locations"]]
            locations = Location.query.filter(Location.id.in_(ids)).all()
            self.locations = locations

        geo_locations = json.get('geoLocations')
        if geo_locations:
            final_locations = []
            for geo in geo_locations:
                gid = geo.get('id')
                if not gid:
                    # new geolocation
                    g = GeoLocation()
                    g.title = geo.get('title')
                    g.type = geo.get('type')
                    g.latlng = 'POINT({} {})'.format(geo.get('lat'), geo.get('lng'))
                    g.comment = geo.get('comment')
                    g.save()
                else:
                    # geolocation exists // update
                    g = GeoLocation.query.get(gid)
                    g.title = geo.get('title')
                    g.type = geo.get('type')
                    g.latlng = 'POINT({} {})'.format(geo.get('lat'), geo.get('lng'))
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
            for event in json["events"]:
                if not "id" in event:
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
            new_medias = []
            for media in json["medias"]:
                # create new medias (new items has no existing id)
                if not "id" in media:
                    m = Media()
                    m = m.from_json(media)
                    m.save()
                else:
                    # must be an existing media
                    m = Media.query.get(media["id"])
                    # update the media (only the title might have changed for now, but possible to update the whole file later)
                    m.from_json(media)
                    m.save()

                new_medias.append(m)
            self.medias = new_medias

        # Related Bulletins (bulletin_relations)
        if "bulletin_relations" in json:
            # collect related bulletin ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["bulletin_relations"]:
                bulletin = Bulletin.query.get(relation["bulletin"]["id"])
                # print ('bulletin to relate', bulletin)
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

        self.publish_date = json.get('publish_date', None)
        if self.publish_date == '':
            self.publish_date = None
        self.documentation_date = json.get('documentation_date', None)
        if self.documentation_date == '':
            self.documentation_date = None
        if "comments" in json:
            self.comments = json["comments"]

        if "status" in json:
            self.status = json["status"]

        return self

    # Compact dict for relationships
    def to_compact(self):
        # locations json
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(
                    {
                        "id": location.id,
                        "title": location.title,
                        "full_string": location.get_full_string(),
                        "lat": location.latitude,
                        "lng": location.longitude
                    }
                )

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
            "source_link_type": getattr(self, 'source_link_type', False),
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
            "comments": self.comments or "",
        }

    # Helper method to handle logic of relating bulletins  (from bulletin)
    def relate_bulletin(self, bulletin, relation=None):
        # if a new bulletin is being created, we must save it to get the id
        if not self.id:
            self.save()

        # Relationships are alwasy forced to go from the lower id to the bigger id (to prevent duplicates)
        # Enough to look up the relationship from the lower to the upper

        # reject self relation
        if self == bulletin:
            # print ('Cant relate bulletin to itself')
            return

        existing_relation = Btob.are_related(self.id, bulletin.id)

        if existing_relation:
            # print ("Relationship exists :: Updating the attributes")
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation (possible from or to the bulletin based on the id comparison)
            new_relation = Btob.relate(self, bulletin)

            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # ------- create revision on the other side of the relationship
            bulletin.create_revision()

    # Helper method to handle logic of relating incidents (from a bulletin)

    def relate_incident(self, incident, relation=None):
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
            incident.create_revision()

    # helper method to relate actors
    def relate_actor(self, actor, relation=None):
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
            actor.create_revision()

    # custom serialization method
    def to_dict(self, mode=None):
        if mode == '2':
            return self.to_mode2()
        if mode == '1':
            return self.min_json()

        # locations json
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(
                    {
                        "id": location.id,
                        "title": location.title,
                        "full_string": location.get_full_string(),
                        "lat": location.latitude,
                        "lng": location.longitude
                    }
                )

        # locations json
        geo_locations_json = []
        if self.geo_locations:
            for geo in self.geo_locations:
                geo_locations_json.append(
                    geo.to_dict()
                )

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
        for relation in self.bulletin_relations:
            bulletin_relations_dict.append(relation.to_dict(exclude=self))

        # Related actors json (actually the associated relationships)
        actor_relations_dict = []
        for relation in self.actor_relations:
            actor_relations_dict.append(relation.to_dict())

        # Related incidents json (actually the associated relationships)
        incident_relations_dict = []
        for relation in self.incident_relations:
            incident_relations_dict.append(relation.to_dict())

        return {
            "class": "Bulletin",
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar,
            "sjac_title": self.sjac_title or None,
            "sjac_title_ar": self.sjac_title_ar or None,
            "originid": self.originid or None,
            # assigned to
            "assigned_to": self.assigned_to.to_compact()
            if self.assigned_to_id
            else None,
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
            "_status": gettext(self.status),
            "review": self.review if self.review else None,
            "review_action": self.review_action if self.review_action else None,
        }

    # custom serialization mode
    def to_mode2(self):
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append(
                    {
                        "id": location.id,
                        "title": location.title,
                        "full_string": location.get_full_string(),
                    }
                )

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

    def to_json(self):
        return json.dumps(self.to_dict())

    @staticmethod
    def get_columns():
        columns = []
        for column in Bulletin.__table__.columns:
            columns.append(column.name)
        return columns


# joint table
actor_sources = db.Table(
    "actor_sources",
    db.Column("source_id", db.Integer, db.ForeignKey("source.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
)

# joint table
actor_labels = db.Table(
    "actor_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
)

# joint table
actor_verlabels = db.Table(
    "actor_verlabels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True
    ),
)

# joint table
actor_events = db.Table(
    "actor_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
)

# joint table
actor_medias = db.Table(
    "actor_medias",
    db.Column("media_id", db.Integer, db.ForeignKey("media.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
)


class Actor(db.Model, BaseMixin):
    """
    SQL Alchemy model for actors
    """
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255))

    description = db.Column(db.Text)

    nickname = db.Column(db.String(255))
    nickname_ar = db.Column(db.String(255))

    first_name = db.Column(db.String(255))
    first_name_ar = db.Column(db.String(255))

    middle_name = db.Column(db.String(255))
    middle_name_ar = db.Column(db.String(255))

    last_name = db.Column(db.String(255))
    last_name_ar = db.Column(db.String(255))

    mother_name = db.Column(db.String(255))
    mother_name_ar = db.Column(db.String(255))

    originid = db.Column(db.String(255))

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

    sources = db.relationship(
        "Source", secondary=actor_sources, backref=db.backref("actors", lazy="dynamic")
    )

    labels = db.relationship(
        "Label", secondary=actor_labels, backref=db.backref("actors", lazy="dynamic")
    )

    ver_labels = db.relationship(
        "Label", secondary=actor_verlabels, backref=db.backref("verlabels_actors", lazy="dynamic"),
    )

    medias = db.relationship(
        "Media", secondary=actor_medias, backref=db.backref("actors", lazy="dynamic")
    )

    events = db.relationship(
        "Event", secondary=actor_events, backref=db.backref("actors", lazy="dynamic")
    )

    # Actors that this actor relate to ->
    actors_to = db.relationship(
        "Atoa", backref="actor_from", foreign_keys="Atoa.actor_id"
    )

    # Actors that relate to this <-
    actors_from = db.relationship(
        "Atoa", backref="actor_to", foreign_keys="Atoa.related_actor_id"
    )

    # Related Bulletins
    related_bulletins = db.relationship(
        "Atob", backref="actor", foreign_keys="Atob.actor_id"
    )

    # Related Incidents
    related_incidents = db.relationship(
        "Itoa", backref="actor", foreign_keys="Itoa.actor_id"
    )

    actor_type = db.Column(db.String(255))
    sex = db.Column(db.String(255))
    age = db.Column(db.String(255))
    civilian = db.Column(db.String(255))
    birth_date = db.Column(db.DateTime)

    birth_place_id = db.Column(db.Integer, db.ForeignKey("location.id"))
    birth_place = db.relationship(
        "Location", backref="actors_born", foreign_keys=[birth_place_id]
    )

    residence_place_id = db.Column(db.Integer, db.ForeignKey("location.id"))
    residence_place = db.relationship(
        "Location", backref="actors_residence_place", foreign_keys=[residence_place_id]
    )
    origin_place_id = db.Column(db.Integer, db.ForeignKey("location.id"))
    origin_place = db.relationship(
        "Location", backref="actors_origin_place", foreign_keys=[origin_place_id]
    )

    occupation = db.Column(db.String(255))
    occupation_ar = db.Column(db.String(255))

    position = db.Column(db.String(255))
    position_ar = db.Column(db.String(255))

    dialects = db.Column(db.String(255))
    dialects_ar = db.Column(db.String(255))

    family_status = db.Column(db.String(255))
    family_status_ar = db.Column(db.String(255))

    ethnography = db.Column(ARRAY(db.String))
    nationality = db.Column(ARRAY(db.String))
    national_id_card = db.Column(db.String(255))

    publish_date = db.Column(db.DateTime, index=True)
    documentation_date = db.Column(db.DateTime, index=True)

    status = db.Column(db.String(255))
    source_link = db.Column(db.String(255))
    source_link_type = db.Column(db.Boolean, default=False)
    comments = db.Column(db.Text)
    # review fields
    review = db.Column(db.Text)
    review_action = db.Column(db.String)

    tsv = db.Column(TSVECTOR)

    if cfg.MISSING_PERSONS:
        last_address = db.Column(db.Text)
        social_networks = db.Column(JSON)
        marriage_history = db.Column(db.String)
        bio_children = db.Column(db.Integer)
        pregnant_at_disappearance = db.Column(db.String)
        months_pregnant = db.Column(db.NUMERIC)
        missing_relatives = db.Column(db.Boolean)
        saw_name = db.Column(db.String)
        saw_address = db.Column(db.Text)
        saw_email = db.Column(db.String)
        saw_phone = db.Column(db.String)
        detained_before = db.Column(db.String)
        seen_in_detention = db.Column(JSON)
        injured = db.Column(JSON)
        known_dead = db.Column(JSON)
        death_details = db.Column(db.Text)
        personal_items = db.Column(db.Text)
        height = db.Column(db.NUMERIC)
        weight = db.Column(db.NUMERIC)
        physique = db.Column(db.String)
        hair_loss = db.Column(db.String)
        hair_type = db.Column(db.String)
        hair_length = db.Column(db.String)
        hair_color = db.Column(db.String)
        facial_hair = db.Column(db.String)
        posture = db.Column(db.Text)
        skin_markings = db.Column(JSON)
        handedness = db.Column(db.String)
        glasses = db.Column(db.String)
        eye_color = db.Column(db.String)
        dist_char_con = db.Column(db.String)
        dist_char_acq = db.Column(db.String)
        physical_habits = db.Column(db.String)
        other = db.Column(db.Text)
        phys_name_contact = db.Column(db.Text)
        injuries = db.Column(db.Text)
        implants = db.Column(db.Text)
        malforms = db.Column(db.Text)
        pain = db.Column(db.Text)
        other_conditions = db.Column(db.Text)
        accidents = db.Column(db.Text)
        pres_drugs = db.Column(db.Text)
        smoker = db.Column(db.String)
        dental_record = db.Column(db.Boolean)
        dentist_info = db.Column(db.Text)
        teeth_features = db.Column(db.Text)
        dental_problems = db.Column(db.Text)
        dental_treatments = db.Column(db.Text)
        dental_habits = db.Column(db.Text)
        case_status = db.Column(db.String)
        # array of objects: name, email,phone, email, address, relationship
        reporters = db.Column(JSON)
        identified_by = db.Column(db.String)
        family_notified = db.Column(db.Boolean)
        hypothesis_based = db.Column(db.Text)
        hypothesis_status = db.Column(db.String)

        # death_cause = db.Column(db.String)
        reburial_location = db.Column(db.String)

    search = db.Column(db.Text, db.Computed("""
         ((((((((((id)::text || ' '::text) || (COALESCE(name, ''::character varying))::text) || ' '::text) ||
                  (COALESCE(name_ar, ''::character varying))::text) || ' '::text) ||
                (COALESCE(originid, ''::character varying))::text) || ' '::text) || COALESCE(description, ''::text)) ||
             ' '::text) || COALESCE(comments, ''::text)
        """))

    __table_args__ = (
        db.Index('ix_actor_search', 'search', postgresql_using="gin", postgresql_ops={'search': 'gin_trgm_ops'}),
    )

    # helper method to create a revision
    def create_revision(self, user_id=None, created=None):
        if not user_id:
            user_id = getattr(current_user, 'id', 1)

        a = ActorHistory(
            actor_id=self.id, data=self.to_dict(), user_id=user_id
        )
        if created:
            a.created_at = created
            a.updated_at = created
        a.save()
        print("created actor revision ")

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

    # populate actor object from json dict
    def from_json(self, json):
        # All text fields

        self.name = json["name"] if "name" in json else None
        self.name_ar = json["name_ar"] if "name_ar" in json else None

        self.nickname = json["nickname"] if "nickname" in json else None
        self.nickname_ar = json["nickname_ar"] if "nickname_ar" in json else None

        self.first_name = json["first_name"] if "first_name" in json else None
        self.first_name_ar = json["first_name_ar"] if "first_name_ar" in json else None

        self.middle_name = json["middle_name"] if "middle_name" in json else None
        self.middle_name_ar = (
            json["middle_name_ar"] if "middle_name_ar" in json else None
        )

        self.last_name = json["last_name"] if "last_name" in json else None
        self.last_name_ar = json["last_name_ar"] if "last_name_ar" in json else None

        self.mother_name = json["mother_name"] if "mother_name" in json else None
        self.mother_name_ar = (
            json["mother_name_ar"] if "mother_name_ar" in json else None
        )

        self.description = json["description"] if "description" in json else None

        self.occupation = json["occupation"] if "occupation" in json else None
        self.occupation_ar = json["occupation_ar"] if "occupation_ar" in json else None
        self.position = json["position"] if "position" in json else None
        self.position_ar = json["position_ar"] if "position_ar" in json else None
        self.dialects = json["dialects"] if "dialects" in json else None
        self.dialects_ar = json["dialects_ar"] if "dialects_ar" in json else None
        self.family_status = json["family_status"] if "family_status" in json else None
        self.family_status_ar = (
            json["family_status_ar"] if "family_status_ar" in json else None
        )
        self.ethnography = json["ethnography"] if "ethnography" in json else []
        self.nationality = json["nationality"] if "nationality" in json else None
        self.national_id_card = (
            json["national_id_card"] if "national_id_card" in json else None
        )

        self.source_link = json["source_link"] if "source_link" in json else None
        self.source_link_type = json.get('source_link_type')

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

        self.sex = json["sex"] if "sex" in json else None
        self.age = json["age"] if "age" in json else None
        self.civilian = json["civilian"] if "civilian" in json else None
        self.actor_type = json["actor_type"] if "actor_type" in json else None

        if "birth_date" in json:
            if json["birth_date"]:
                self.birth_date = json["birth_date"]

        if "birth_place" in json:
            if json["birth_place"] and "id" in json["birth_place"]:
                self.birth_place_id = json["birth_place"]["id"]

        if "residence_place" in json:
            if json["residence_place"] and "id" in json["residence_place"]:
                self.residence_place_id = json["residence_place"]["id"]

        if "origin_place" in json:
            if json["origin_place"] and "id" in json["origin_place"]:
                self.origin_place_id = json["origin_place"]["id"]

        # Events
        if "events" in json:
            new_events = []
            for event in json["events"]:
                if not "id" in event:
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
            new_medias = []
            for media in json["medias"]:
                # create new medias (new items has no existing id)
                if not "id" in media:
                    m = Media()
                    m = m.from_json(media)
                    m.save()
                else:
                    # must be an existing media
                    m = Media.query.get(media["id"])
                    # update the media (only the title might have changed for now, but possible to update the whole file later)
                    m.from_json(media)
                    m.save()

                new_medias.append(m)
            self.medias = new_medias

        self.publish_date = json.get('publish_date', None)
        if self.publish_date == '':
            self.publish_date = None
        self.documentation_date = json.get('documentation_date', None)
        if self.documentation_date == '':
            self.documentation_date = None

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
                    # print ('deleting', r)
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
                    # print ('deleting', r)
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

        # Missing Persons
        if cfg.MISSING_PERSONS:
            self.last_address = json.get('last_address')
            self.marriage_history = json.get('marriage_history')
            self.bio_children = json.get('bio_children')
            self.pregnant_at_disappearance = json.get('pregnant_at_disappearance')
            self.months_pregnant = json.get('months_pregnant')
            self.missing_relatives = json.get('missing_relatives')
            self.saw_name = json.get('saw_name')
            self.saw_address = json.get('saw_address')
            self.saw_phone = json.get('saw_phone')
            self.saw_email = json.get('saw_email')
            self.seen_in_detention = json.get('seen_in_detention')
            # Flag json fields for saving
            flag_modified(self, 'seen_in_detention')
            self.injured = json.get('injured')
            flag_modified(self, 'injured')
            self.known_dead = json.get('known_dead')
            flag_modified(self, 'known_dead')
            self.death_details = json.get('death_details')
            self.personal_items = json.get('personal_items')
            self.height = json.get('height')
            self.weight = json.get('weight')
            self.physique = json.get('physique')
            self.hair_loss = json.get('hair_loss')
            self.hair_type = json.get('hair_type')
            self.hair_length = json.get('hair_length')
            self.hair_color = json.get('hair_color')
            self.facial_hair = json.get('facial_hair')
            self.posture = json.get('posture')
            self.skin_markings = json.get('skin_markings')
            flag_modified(self, 'skin_markings')
            self.handedness = json.get('handedness')
            self.eye_color = json.get('eye_color')
            self.glasses = json.get('glasses')
            self.dist_char_con = json.get('dist_char_con')
            self.dist_char_acq = json.get('dist_char_acq')
            self.physical_habits = json.get('physical_habits')
            self.other = json.get('other')
            self.phys_name_contact = json.get('phys_name_contact')
            self.injuries = json.get('injuries')
            self.implants = json.get('implants')
            self.malforms = json.get('malforms')
            self.pain = json.get('pain')
            self.other_conditions = json.get('other_conditions')
            self.accidents = json.get('accidents')
            self.pres_drugs = json.get('pres_drugs')
            self.smoker = json.get('smoker')
            self.dental_record = json.get('dental_record')
            self.dentist_info = json.get('dentist_info')
            self.teeth_features = json.get('teeth_features')
            self.dental_problems = json.get('dental_problems')
            self.dental_treatments = json.get('dental_treatments')
            self.dental_habits = json.get('dental_habits')
            self.case_status = json.get('case_status')
            self.reporters = json.get('reporters')
            flag_modified(self, 'reporters')
            self.identified_by = json.get('identified_by')
            self.family_notified = json.get('family_notified')
            self.reburial_location = json.get('reburial_location')
            self.hypothesis_based = json.get('hypothesis_based')
            self.hypothesis_status = json.get('hypothesis_status')

        return self

    def mp_json(self):
        mp = {}
        mp['MP'] = True
        mp['last_address'] = getattr(self, 'last_address')
        mp['marriage_history'] = getattr(self, 'marriage_history')
        mp['bio_children'] = getattr(self, 'bio_children')
        mp['pregnant_at_disappearance'] = getattr(self, 'pregnant_at_disappearance')
        mp['months_pregnant'] = str(self.months_pregnant) if self.months_pregnant else None
        mp['missing_relatives'] = getattr(self, 'missing_relatives')
        mp['saw_name'] = getattr(self, 'saw_name')
        mp['saw_address'] = getattr(self, 'saw_address')
        mp['saw_phone'] = getattr(self, 'saw_phone')
        mp['saw_email'] = getattr(self, 'saw_email')
        mp['seen_in_detention'] = getattr(self, 'seen_in_detention')
        mp['injured'] = getattr(self, 'injured')
        mp['known_dead'] = getattr(self, 'known_dead')
        mp['death_details'] = getattr(self, 'death_details')
        mp['personal_items'] = getattr(self, 'personal_items')
        mp['height'] = str(self.height) if self.height else None
        mp['weight'] = str(self.weight) if self.weight else None
        mp['physique'] = getattr(self, 'physique')
        mp['_physique'] = getattr(self, 'physique')

        mp['hair_loss'] = getattr(self, 'hair_loss')
        mp['_hair_loss'] = gettext(self.hair_loss)

        mp['hair_type'] = getattr(self, 'hair_type')
        mp['_hair_type'] = gettext(self.hair_type)

        mp['hair_length'] = getattr(self, 'hair_length')
        mp['_hair_length'] = gettext(self.hair_length)

        mp['hair_color'] = getattr(self, 'hair_color')
        mp['_hair_color'] = gettext(self.hair_color)

        mp['facial_hair'] = getattr(self, 'facial_hair')
        mp['_facial_hair'] = gettext(self.facial_hair)

        mp['posture'] = getattr(self, 'posture')
        mp['skin_markings'] = getattr(self, 'skin_markings')
        if self.skin_markings and self.skin_markings.get('opts'):
            mp['_skin_markings'] = [gettext(item) for item in self.skin_markings['opts']]


        mp['handedness'] = getattr(self, 'handedness')
        mp['_handedness'] = gettext(self.handedness)
        mp['eye_color'] = getattr(self, 'eye_color')
        mp['_eye_color'] = gettext(self.eye_color)

        mp['glasses'] = getattr(self, 'glasses')
        mp['dist_char_con'] = getattr(self, 'dist_char_con')
        mp['dist_char_acq'] = getattr(self, 'dist_char_acq')
        mp['physical_habits'] = getattr(self, 'physical_habits')
        mp['other'] = getattr(self, 'other')
        mp['phys_name_contact'] = getattr(self, 'phys_name_contact')
        mp['injuries'] = getattr(self, 'injuries')
        mp['implants'] = getattr(self, 'implants')
        mp['malforms'] = getattr(self, 'malforms')
        mp['pain'] = getattr(self, 'pain')
        mp['other_conditions'] = getattr(self, 'other_conditions')
        mp['accidents'] = getattr(self, 'accidents')
        mp['pres_drugs'] = getattr(self, 'pres_drugs')
        mp['smoker'] = getattr(self, 'smoker')
        mp['dental_record'] = getattr(self, 'dental_record')
        mp['dentist_info'] = getattr(self, 'dentist_info')
        mp['teeth_features'] = getattr(self, 'teeth_features')
        mp['dental_problems'] = getattr(self, 'dental_problems')
        mp['dental_treatments'] = getattr(self, 'dental_treatments')
        mp['dental_habits'] = getattr(self, 'dental_habits')
        mp['case_status'] = getattr(self, 'case_status')
        mp['_case_status'] = gettext(self.case_status)
        mp['reporters'] = getattr(self, 'reporters')
        mp['identified_by'] = getattr(self, 'identified_by')
        mp['family_notified'] = getattr(self, 'family_notified')
        mp['reburial_location'] = getattr(self, 'reburial_location')
        mp['hypothesis_based'] = getattr(self, 'hypothesis_based')
        mp['hypothesis_status'] = getattr(self, 'hypothesis_status')
        return mp

    # Compact dict for relationships
    def to_compact(self):

        # sources json
        sources_json = []
        if self.sources and len(self.sources):
            for source in self.sources:
                sources_json.append({"id": source.id, "title": source.title})

        return {
            "id": self.id,
            "name": self.name,
            "originid": self.originid or None,
            "sources": sources_json,
            "description": self.description or None,
            "source_link": self.source_link or None,
            "source_link_type": getattr(self, "source_link_type"),
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
        }

    # Helper method to handle logic of relating actors (from actor)

    def relate_actor(self, actor, relation=None):

        # if a new actor is being created, we must save it to get the id
        if not self.id:
            self.save()

        # Relationships are alwasy forced to go from the lower id to the bigger id (to prevent duplicates)
        # Enough to look up the relationship from the lower to the upper

        # reject self relation
        if self == actor:
            # print ('Cant relate bulletin to itself')
            return

        existing_relation = Atoa.are_related(self.id, actor.id)
        if existing_relation:
            # print ("Relationship exists :: Updating the attributes")
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation (possible from or to the actor based on the id comparison)
            new_relation = Atoa.relate(self, actor)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # revision for related actor
            actor.create_revision()

    # Helper method to handle logic of relating bulletin (from am actor)
    def relate_bulletin(self, bulletin, relation=None):
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
            bulletin.create_revision()

    # Helper method to handle logic of relating incidents (from an actor)
    def relate_incident(self, incident, relation=None):
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
            incident.create_revision()

    # custom serialization method
    def to_dict(self, mode=None):

        if mode == '1':
            return self.min_json()
        if mode == '2':
            return self.to_mode2()

        # Sources json
        sources_json = []
        if self.sources and len(self.sources):
            for source in self.sources:
                sources_json.append({"id": source.id, "title": source.title})

        # Labels json
        labels_json = []
        if self.labels and len(self.labels):
            for label in self.labels:
                labels_json.append({"id": label.id, "title": label.title})

        # verified labels json
        ver_labels_json = []
        if self.ver_labels and len(self.ver_labels):
            for vlabel in self.ver_labels:
                ver_labels_json.append({"id": vlabel.id, "title": vlabel.title})

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

        actor_relations_dict = []
        for relation in self.actor_relations:
            actor_relations_dict.append(relation.to_dict(exclude=self))

        bulletin_relations_dict = []
        for relation in self.bulletin_relations:
            bulletin_relations_dict.append(relation.to_dict())

        incident_relations_dict = []
        for relation in self.incident_relations:
            incident_relations_dict.append(relation.to_dict())

        actor = {
            "class": "Actor",
            "id": self.id,
            "originid": self.originid or None,
            "name": self.name or None,
            "name_ar": getattr(self, 'name_ar'),
            "description": self.description or None,
            "nickname": self.nickname or None,
            "nickname_ar": getattr(self, 'nickname_ar'),
            "first_name": self.first_name or None,
            "first_name_ar": self.first_name_ar or None,
            "middle_name": self.middle_name or None,
            "middle_name_ar": self.middle_name_ar or None,
            "last_name": self.last_name or None,
            "last_name_ar": self.last_name_ar or None,
            "mother_name": self.mother_name or None,
            "mother_name_ar": self.mother_name_ar or None,
            "sex": self.sex,
            "_sex": gettext(self.sex),
            "age": self.age,
            "_age": gettext(self.age),
            "civilian": self.civilian or None,
            "_civilian": gettext(self.civilian),
            "actor_type": self.actor_type,
            "_actor_type": gettext(self.actor_type),
            "occupation": self.occupation or None,
            "occupation_ar": self.occupation_ar or None,
            "position": self.position or None,
            "position_ar": self.position_ar or None,
            "dialects": self.dialects or None,
            "dialects_ar": self.dialects_ar or None,
            "family_status": self.family_status or None,
            "family_status_ar": self.family_status_ar or None,
            "ethnography": self.ethnography or None,

            "nationality": self.nationality or None,
            "national_id_card": self.national_id_card or None,
            # assigned to
            "assigned_to": {
                "id": self.assigned_to.id,
                "name": self.assigned_to.name,
                "email": self.assigned_to.email,
            }
            if self.assigned_to_id
            else None,
            # first peer reviewer
            "first_peer_reviewer": {
                "id": self.first_peer_reviewer.id,
                "name": self.first_peer_reviewer.name,
                "email": self.first_peer_reviewer.email,
            }
            if self.first_peer_reviewer_id
            else None,
            "source_link": self.source_link or None,
            "source_link_type": getattr(self, "source_link_type"),
            "comments": self.comments or None,
            "sources": sources_json,
            "labels": labels_json,
            "verLabels": ver_labels_json,
            "events": events_json,
            "medias": medias_json,
            "actor_relations": actor_relations_dict,
            "bulletin_relations": bulletin_relations_dict,
            "incident_relations": incident_relations_dict,
            "birth_place": self.birth_place.to_dict() if self.birth_place else None,
            "residence_place": self.residence_place.to_dict()
            if self.residence_place
            else None,
            "origin_place": self.origin_place.to_dict() if self.origin_place else None,

            "birth_date": self.birth_date.strftime("%Y-%m-%d")
            if self.birth_date
            else None,
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
            "status": self.status,
            "_status": gettext(self.status),
            "review": self.review if self.review else None,
            "review_action": self.review_action if self.review_action else None,
        }
        # custom translation handler for ethnography and nationality
        if self.ethnography:
            actor['_ethnography'] = [gettext(item) for item in self.ethnography]
        if self.nationality:
            actor['_nationality'] = [gettext(item) for item in self.nationality]
        # handle missing actors mode
        if cfg.MISSING_PERSONS:
            mp = self.mp_json()
            actor.update(mp)

        return actor

    def to_mode2(self):

        # Sources json
        sources_json = []
        if self.sources and len(self.sources):
            for source in self.sources:
                sources_json.append({"id": source.id, "title": source.title})

        return {
            "class": "Actor",
            "id": self.id,
            "originid": self.originid or None,
            "name": self.name or None,
            "description": self.description or None,
            "comments": self.comments or None,
            "sources": sources_json,
            "publish_date": DateHelper.serialize_datetime(self.publish_date),
            "documentation_date": DateHelper.serialize_datetime(self.documentation_date),
            "status": self.status if self.status else None,

        }

    def to_json(self):
        return json.dumps(self.to_dict())



    def validate(self):
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

    # Exclude the primary bulletin from output to get only the related/relating bulletin
    # custom serialization method
    def to_dict(self):

        return {
            "bulletin": self.bulletin.to_compact(),
            "incident": self.incident.to_compact(),
            "related_as": self.related_as,
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data
    def from_json(self, relation=None):
        if relation:
            self.probability = (
                relation["probability"] if "probability" in relation else None
            )
            self.related_as = (
                relation["related_as"] if "related_as" in relation else None
            )
            self.comment = relation["comment"] if "comment" in relation else None
            print("Relation has been updated.")
        else:
            print("Relation was not updated.")
        return self


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
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itoas", foreign_keys=[user_id])

    # custom serialization method
    def to_dict(self):

        return {
            "actor": self.actor.to_compact(),
            "incident": self.incident.to_compact(),
            "related_as": self.related_as,
            "probability": self.probability,
            "comment": self.comment,
            "user_id": self.user_id,
        }

    # this will update only relationship data, (populates it from json dict)
    def from_json(self, relation=None):
        if relation:
            self.probability = (
                relation["probability"] if "probability" in relation else None
            )
            self.related_as = (
                relation["related_as"] if "related_as" in relation else None
            )
            self.comment = relation["comment"] if "comment" in relation else None
            print("Relation has been updated.")
        else:
            print("Relation was not updated.")
        return self


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
    related_incident_id = db.Column(
        db.Integer, db.ForeignKey("incident.id"), primary_key=True
    )

    # Relationship extra fields
    related_as = db.Column(db.Integer)
    probability = db.Column(db.Integer)
    comment = db.Column(db.Text)

    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_itois", foreign_keys=[user_id])

    # Check if two incidents are related , if so return the relation, otherwise false
    @staticmethod
    def are_related(a_id, b_id):

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
    def get_other_id(self, id):
        if id in (self.incident_id, self.related_incident_id):
            return (
                self.incident_id
                if id == self.related_incident_id
                else self.related_incident_id
            )
        return None

    # Create and return a relation between two bulletins making sure the relation goes from the lower id to the upper id
    @staticmethod
    def relate(a, b):
        f, t = min(a.id, b.id), max(a.id, b.id)
        return Itoi(incident_id=f, related_incident_id=t)

    # custom serialization method
    def to_dict(self, exclude=None):
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
            incident = (
                self.incident_to
                if exclude == self.incident_from
                else self.incident_from
            )
            return {
                "incident": incident.to_compact(),
                "related_as": self.related_as,
                "probability": self.probability,
                "comment": self.comment,
                "user_id": self.user_id,
            }

    # this will update only relationship data
    def from_json(self, relation=None):
        if relation:
            self.probability = (
                relation["probability"] if "probability" in relation else None
            )
            self.related_as = (
                relation["related_as"] if "related_as" in relation else None
            )
            self.comment = relation["comment"] if "comment" in relation else None
            print("Relation has been updated.")
        else:
            print("Relation was not updated.")
        return self


class PotentialViolation(db.Model, BaseMixin):
    """
    SQL Alchemy model for potential violations
    """
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    title_ar = db.Column(db.String)

    # to serialize data
    def to_dict(self):
        return {"id": self.id, "title": self.title}

    def to_json(self):
        return json.dumps(self.to_dict())

    # load from json dit
    def from_json(self, json):
        self.title = json["title"]
        return self

    # import csv data in to db items
    @staticmethod
    def import_csv(file_storage):
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        db.session.bulk_insert_mappings(PotentialViolation, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from potential_violation").scalar()
        db.session.execute(
            "alter sequence potential_violation_id_seq restart with {}".format(max_id)
        )
        db.session.commit()
        print("Potential Violation ID counter updated.")
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
    def to_dict(self):
        return {"id": self.id, "title": self.title}

    def to_json(self):
        return json.dumps(self.to_dict())

    # populate from json dict
    def from_json(self, json):
        self.title = json["title"]
        return self

    # import csv data into db items
    @staticmethod
    def import_csv(file_storage):
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        db.session.bulk_insert_mappings(ClaimedViolation, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute("select max(id)+1  from claimed_violation").scalar()
        db.session.execute(
            "alter sequence claimed_violation_id_seq restart with {}".format(max_id)
        )
        db.session.commit()
        print("Claimed Violation ID counter updated.")
        return ""


# joint table
incident_locations = db.Table(
    "incident_locations",
    db.Column(
        "location_id", db.Integer, db.ForeignKey("location.id"), primary_key=True
    ),
    db.Column(
        "incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True
    ),
)

# joint table
incident_labels = db.Table(
    "incident_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True
    ),
)

# joint table
incident_events = db.Table(
    "incident_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column(
        "incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True
    ),
)

# joint table
incident_potential_violations = db.Table(
    "incident_potential_violations",
    db.Column("potentialviolation_id", db.Integer, db.ForeignKey("potential_violation.id"), primary_key=True),
    db.Column(
        "incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True
    ),
)

# joint table
incident_claimed_violations = db.Table(
    "incident_claimed_violations",
    db.Column("claimedviolation_id", db.Integer, db.ForeignKey("claimed_violation.id"), primary_key=True),
    db.Column(
        "incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True
    ),
)


class Incident(db.Model, BaseMixin):
    """
    SQL Alchemy model for incidents
    """
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
    )

    # Related Actors
    related_actors = db.relationship(
        "Itoa", backref="incident", foreign_keys="Itoa.incident_id"
    )

    # Related Bulletins
    related_bulletins = db.relationship(
        "Itob", backref="incident", foreign_keys="Itob.incident_id"
    )

    # Related Incidents
    # Incidents that this incident relate to ->
    incidents_to = db.relationship(
        "Itoi", backref="incident_from", foreign_keys="Itoi.incident_id"
    )

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

    search = db.Column(db.Text, db.Computed("""
             ((((((((id)::text || ' '::text) || (COALESCE(title, ''::character varying))::text) || ' '::text) ||
                (COALESCE(title_ar, ''::character varying))::text) || ' '::text) || COALESCE(description, ''::text)) ||
             ' '::text) || COALESCE(comments, ''::text)
            """))

    __table_args__ = (
        db.Index('ix_incident_search', 'search', postgresql_using="gin", postgresql_ops={'search': 'gin_trgm_ops'}),
    )

    # helper method to create a revision
    def create_revision(self, user_id=None, created=None):
        if not user_id:
            user_id = getattr(current_user, 'id', 1)
        i = IncidentHistory(
            incident_id=self.id, data=self.to_dict(), user_id=user_id
        )
        if created:
            i.created_at = created
            i.updated_at = created
        i.save()
        print("created incident revision ")

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

    # populate model from json dict
    def from_json(self, json):
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
            potential_violations = PotentialViolation.query.filter(PotentialViolation.id.in_(ids)).all()
            self.potential_violations = potential_violations

        # Claimed Violations
        if "claimed_violations" in json:
            ids = [cv["id"] for cv in json["claimed_violations"]]
            claimed_violations = ClaimedViolation.query.filter(ClaimedViolation.id.in_(ids)).all()
            self.claimed_violations = claimed_violations

        # Events
        if "events" in json:
            new_events = []
            for event in json["events"]:
                if not "id" in event:
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
                if not (r.actor_id in rel_ids):
                    rel_actor = r.actor
                    # print ('deleting', r)
                    r.delete()

                    # -revision related actor
                    rel_actor.create_revision()

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
                    # print ('deleting', r)
                    rel_bulletin = r.bulletin
                    r.delete()

                    # -revision related bulletin
                    rel_bulletin.create_revision()

        # Related Incidnets (incident_relations)
        if "incident_relations" in json:
            # collect related incident ids (helps with finding removed ones)
            rel_ids = []
            for relation in json["incident_relations"]:
                incident = Incident.query.get(relation["incident"]["id"])
                # print ('incident to relate', incident)
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
                    print("deleting", r)
                    r.delete()

                    # - revision related incident
                    Incident.query.get(rid).create_revision()

        if "comments" in json:
            self.comments = json["comments"]

        if "status" in json:
            self.status = json["status"]

        return self

    # Compact dict for relationships
    def to_compact(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or None,
        }

    # Helper method to handle logic of relating incidents
    def relate_incident(self, incident, relation=None):

        # if a new actor is being created, we must save it to get the id
        if not self.id:
            self.save()

        # Relationships are alwasy forced to go from the lower id to the bigger id (to prevent duplicates)
        # Enough to look up the relationship from the lower to the upper

        # reject self relation
        if self == incident:
            # print ('Cant relate incident to itself')
            return

        existing_relation = Itoi.are_related(self.id, incident.id)
        if existing_relation:
            # print ("Relationship exists :: Updating the attributes")
            existing_relation.from_json(relation)
            existing_relation.save()

        else:
            # Create new relation (possible from or to the actor based on the id comparison)
            new_relation = Itoi.relate(self, incident)
            # update relation data
            new_relation.from_json(relation)
            new_relation.save()

            # -revision related incident
            incident.create_revision()

    # Helper method to handle logic of relating actors
    def relate_actor(self, actor, relation=None):
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
            actor.create_revision()

    # Helper method to handle logic of relating bulletins
    def relate_bulletin(self, bulletin, relation=None):
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
            bulletin.create_revision()

    # custom serialization method
    def to_dict(self, mode=None):
        if mode == '1':
            return self.min_json()
        if mode == '2':
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
                locations_json.append({
                    "id": location.id,
                    "title": location.title,
                    "full_string": location.get_full_string(),
                })

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

        actor_relations_dict = []
        for relation in self.actor_relations:
            actor_relations_dict.append(relation.to_dict())

        bulletin_relations_dict = []
        for relation in self.bulletin_relations:
            bulletin_relations_dict.append(relation.to_dict())

        incident_relations_dict = []
        for relation in self.incident_relations:
            incident_relations_dict.append(relation.to_dict(exclude=self))

        return {
            "class": "Incident",
            "id": self.id,
            "title": self.title or None,
            "description": self.description or None,
            # assigned to
            "assigned_to": {
                "id": self.assigned_to.id,
                "name": self.assigned_to.name,
                "email": self.assigned_to.email,
            }
            if self.assigned_to_id
            else None,
            # first peer reviewer
            "first_peer_reviewer": {
                "id": self.first_peer_reviewer.id,
                "name": self.first_peer_reviewer.name,
                "email": self.first_peer_reviewer.email,
            }
            if self.first_peer_reviewer_id
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
        }

    # custom serialization mode
    def to_mode2(self):

        # Labels json
        labels_json = []
        if self.labels and len(self.labels):
            for label in self.labels:
                labels_json.append({"id": label.id, "title": label.title})

        # Locations json
        locations_json = []
        if self.locations and len(self.locations):
            for location in self.locations:
                locations_json.append({
                    "id": location.id,
                    "title": location.title,
                    "full_string": location.get_full_string(),
                })

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

    def to_json(self):
        return json.dumps(self.to_dict())


# ----------------------------------- History Tables (Versioning) ------------------------------------


class BulletinHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for bulletin revisions
    """
    id = db.Column(db.Integer, primary_key=True)
    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"), index=True)
    bulletin = db.relationship(
        "Bulletin", backref="history", foreign_keys=[bulletin_id]
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="bulletin_revisions", foreign_keys=[user_id])

    # serialize
    def to_dict(self):
        return {
            "id": self.id,
            "data": self.data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact(),
        }

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True)


# how to search
# Bulletin.query.filter(Bulletin.tsv.op('@@')(func.plainto_tsquery('search_term')))


# register an event listener to store version histories History tables
@event.listens_for(Bulletin, "after_insert")
def version_trigger(mapper, connection, bulletin: Bulletin):
    # user semi-raw query to avoid session conflicts
    # connection.execute(BulletinHistory.__table__.insert().values(bulletin_id=bulletin.id,version=0,data=bulletin.to_dict(),user_id=current_user.id))
    # bulletin.create_revision()
    pass


# unused for now
@event.listens_for(db.session, "after_commit")
def after_commit(x):
    pass


# --------------------------------- Actors History + Indexers -------------------------------------


class ActorHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for actor revisions
    """
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), index=True)
    actor = db.relationship("Actor", backref="history", foreign_keys=[actor_id])
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="actor_revisions", foreign_keys=[user_id])

    # serialize
    def to_dict(self):
        return {
            "id": self.id,
            "data": self.data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact(),
        }

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True)


# how to search
# Bulletin.query.filter(Bulletin.tsv.op('@@')(func.plainto_tsquery('search_term')))


# register an event listener to store version histories History tables
@event.listens_for(Actor, "after_insert")
def version_trigger(mapper, connection, bulletin: Bulletin):
    # user semi-raw query to avoid session conflicts
    # connection.execute(BulletinHistory.__table__.insert().values(bulletin_id=bulletin.id,version=0,data=bulletin.to_dict(),user_id=current_user.id))
    # bulletin.create_revision()
    pass


# --------------------------------- Incident History + Indexers -------------------------------------


class IncidentHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for incident revisions
    """
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), index=True)
    incident = db.relationship(
        "Incident", backref="history", foreign_keys=[incident_id]
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="incident_revisions", foreign_keys=[user_id])

    # serialize
    def to_dict(self):
        return {
            "id": self.id,
            "data": self.data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact(),
        }

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True)


# register an event listener to store version histories History tables
@event.listens_for(Incident, "after_insert")
def version_trigger(mapper, connection, incident: Incident):
    # user semi-raw query to avoid session conflicts
    # connection.execute(BulletinHistory.__table__.insert().values(bulletin_id=bulletin.id,version=0,data=bulletin.to_dict(),user_id=current_user.id))
    # bulletin.create_revision()
    pass


class Activity(db.Model, BaseMixin):
    """
    SQL Alchemy model for activity
    """

    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_CREATE = 'CREATE-REVISION'
    ACTION_BULK_UPDATE = "BULK-UPDATE"
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    action = db.Column(db.String(100))
    subject = db.Column(JSON)
    tag = db.Column(db.String(100))

    # serialize data
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'subject': self.subject,
            'tag': self.tag,
            'created_at': DateHelper.serialize_datetime(self.created_at),

        }

    # helper static method to create different type of activities (tags)
    @staticmethod
    def create(user, action, subject, tag):
        try:
            activity = Activity()
            activity.user_id = user.id
            activity.action = action
            activity.subject = subject
            activity.tag = tag
            activity.save()

        except Exception:
            print('Oh Noes! Error creating activity.')


class Settings(db.Model, BaseMixin):
    """Global Application Settings. (SQL Alchemy model)"""
    id = db.Column(db.Integer, primary_key=True)
    darkmode = db.Column(db.Boolean, default=False)
    api_key = db.Column(db.String)

    # can be used to generate custom api keys for different integratinos
    @staticmethod
    def get_api_key():
        s = Settings.query.first()
        if s and s.api_key:
            return s.api_key
        else:
            return ''


class Etl(db.Model, BaseMixin):
    id = db.Column(db.Integer, primary_key=True)
    bulletin_id = db.Column(db.Integer, db.ForeignKey('bulletin.id'))
    bulletin = db.relationship('Bulletin', backref='etl')
    meta = db.Column(JSON)


class Query(db.Model, BaseMixin):
    """
    SQL Alchemy model for saved searches
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref="queries", foreign_keys=[user_id])
    data = db.Column(JSON)

    # serialize data 
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'data': self.data,
        }

    def to_json(self):
        return json.dumps(self.to_dict())


class Mapping(db.Model, BaseMixin):
    """
    SQL Alchemy model for sheet import mappings
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref="mappings", foreign_keys=[user_id])
    data = db.Column(JSON)

    # serialize data
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'data': self.data,
        }

    def to_json(self):
        return json.dumps(self.to_dict())


class Log(db.Model, BaseMixin):
    """
    SQL Alchemy model for log table
    """
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String, index=True)
    name = db.Column(db.String)
    subject = db.Column(db.String)
    type = db.Column(db.String)
    tag = db.Column(db.String, index=True)
    status = db.Column(db.String, index=True)
    meta = db.Column(JSON)

    # helper static method to create log entries
    @staticmethod
    def create(name, subject, type, tag, status, meta=None):
        try:
            log = Log()
            log.name = name
            log.subject = subject
            log.type = type
            log.tag = tag
            log.status = status
            log.meta = meta
            log.save()

        except Exception as e:
            print('Error creating log entry:  {}'.format(e))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'tag': self.tag,
            'status': self.status,
            'meta': self.meta
        }

    def __repr__(self):
        return '<{} - {}>'.format(self.id, self.name)
