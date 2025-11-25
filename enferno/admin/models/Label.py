import json
from tempfile import NamedTemporaryFile
from typing import Any, Optional

import pandas as pd
import werkzeug
from sqlalchemy import text

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Label(db.Model, BaseMixin):
    """
    SQL Alchemy model for labels
    """

    MAX_TREE_DEPTH = 5

    __table_args__ = (
        db.CheckConstraint("id != parent_label_id", name="label_no_self_parent"),
        db.UniqueConstraint("parent_label_id", "title", name="label_unique_sibling_title"),
        {"extend_existing": True},
    )

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
            "updated_at": (
                DateHelper.serialize_datetime(self.updated_at) if self.updated_at else None
            ),
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
                  with recursive lcte (id, parent_label_id, title) as (
                  select id, parent_label_id, title from label where id in :qstr union all 
                  select x.id, x.parent_label_id, x.title from lcte c, label x where x.parent_label_id = c.id)
                  select * from lcte;
                  """
        with db.engine.connect() as connection:
            result = connection.execute(text(query), {"qstr": qstr})
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
        max_id = db.session.execute(text("select max(id)+1 from label")).scalar()
        db.session.execute(text("alter sequence label_id_seq restart with :m"), {"m": max_id})
        db.session.commit()
        return ""
