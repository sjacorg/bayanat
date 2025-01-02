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
        with db.engine.connect() as connection:
            result = connection.execute(text(query), {"qstr": qstr})
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
        max_id = db.session.execute(text("select max(id)+1 from source")).scalar()
        db.session.execute(text("alter sequence source_id_seq restart with :m"), {"m": max_id})
        db.session.commit()

        return ""
